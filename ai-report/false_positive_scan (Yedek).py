import json
import requests
from bs4 import BeautifulSoup
import os
from openai import OpenAI
import urllib.parse

# ==== AI Seçimi ====
use_gemini = True  # True: Gemini API kullan, False: Yerel AI kullan

# ==== Ayarlar ====
base_url = "http://192.168.1.204:1235"
login_url = f"{base_url}/DVWA/login.php"
username = "admin"
password = "password"
zap_report_path = "/home/ubuntu-jenkins/Desktop/ai-report/zap_json.json"
output_raw = "/home/ubuntu-jenkins/Desktop/ai-report/json-reports/zap_results.json"
output_filtered = "/home/ubuntu-jenkins/Desktop/ai-report/json-reports/filtered_results.json"
REQUEST_TIMEOUT = 15  # Saniye cinsinden zaman aşımı süresi
gemini_api_key = "SECRET"

# ==== Çıktı klasörünün varlığından emin ol ====
os.makedirs(os.path.dirname(output_raw), exist_ok=True)

# ==== Yerel AI İstemcisi ====
ai_client = OpenAI(
    api_key="dummy_value",
    base_url="http://192.168.1.200:12434/engines/llama.cpp/v1"
)

# ==== Geliştirilmiş Prompt Fonksiyonu ====
def create_ai_prompt_with_baseline(vuln_type, request_str, baseline_context, attack_context):
    """AI'a karşılaştırma yapabilmesi için baseline ve saldırı yanıtlarını içeren bir prompt oluşturur."""
    return f"""
As a senior penetration tester, your task is to analyze a security finding by comparing a baseline (normal) response with an attack response.

Vulnerability Type: {vuln_type}

--- Request Sent by Scanner (Payload Included) ---
{request_str}

--- Baseline Context (Normal Request, No Payload) ---
{baseline_context}

--- Attack Context (After Sending Payload) ---
{attack_context}
---

Analysis Task:
1. Compare the 'Attack Context' to the 'Baseline Context'.
2. Did the payload cause a meaningful, security-related change in the response (e.g., execution of script tags, SQL error messages, unexpected headers, significant content difference)?
3. Based on this comparison, is the vulnerability finding a false positive?

Respond with a single word: "true" if it is a false positive, or "false" if it is a real vulnerability. Do not provide any explanation.
"""

def get_response_context(response: requests.Response) -> str:
    """Bir HTTP yanıtından başlıkları ve gövdeyi birleştirerek AI için bağlam oluşturur."""
    headers = json.dumps(dict(response.headers), indent=2)
    body = response.text[:10000] # Daha fazla bağlam için limiti artır
    return f"Status Code: {response.status_code}\nHeaders:\n{headers}\n\nBody Snippet:\n{body}"

# ==== AI Değerlendirme Fonksiyonları ====
def evaluate_with_ai_model(prompt: str) -> bool:
    """Ortak AI değerlendirme mantığı."""
    if use_gemini:
        try:
            import google.generativeai as genai
            from google.api_core import exceptions as google_exceptions

            genai.configure(api_key=gemini_api_key)
            config = genai.types.GenerationConfig(temperature=0.0, top_k=1, max_output_tokens=8)
            model = genai.GenerativeModel("gemini-1.5-flash", generation_config=config)
            response = model.generate_content(prompt)
            reply = response.text.strip().lower().replace('"', '').replace('.', '')
            return reply == "true"
        
        # if reached to rate limit
        except google_exceptions.ResourceExhausted as e:
            #print(f"[!] Gemini API rate limit reached. Assuming it's a real vulnerability (false_positive=False).")
            return False # Rate limit'e ulaşıldığında "gerçek zafiyet" olarak kabul et

        except ImportError:
            print("[!] Gemini library not found. Install it with `pip install google-generativeai`.")
            return False 
        except Exception as e:
            print(f"[!] Gemini evaluation error: {e}")
            return False
    else: # Yerel AI
        try:
            response = ai_client.chat.completions.create(
                model="ai/qwen3:0.6B-Q4_K_M",
                messages=[
                    {"role": "system", "content": "You are a helpful security analyst AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            reply = response.choices[0].message.content.strip().lower().replace('"', '').replace('.', '')
            return reply == "true"
        except Exception as e:
            print(f"[!] Local AI evaluation error: {e}\n")
            return False

# ==== 1. Oturum başlat ve giriş yap ====
print("Attempting to log in to DVWA...")
session = requests.Session()
try:
    resp = session.get(login_url, timeout=REQUEST_TIMEOUT)
    soup = BeautifulSoup(resp.text, "html.parser")
    user_token = soup.find("input", {"name": "user_token"})["value"]
except requests.exceptions.RequestException as e:
    print(f"[✗] Login failed: Could not connect to {login_url}. Error: {e}")
    exit(1)
except (KeyError, TypeError):
    print("[✗] Login failed: Could not find user_token on the page.")
    exit(1)

headers = {"Host": "192.168.1.204:1235", "User-Agent": "Mozilla/5.0", "Origin": base_url, "Referer": login_url}
session.cookies.set("security", "low")
login_data = {"username": username, "password": password, "Login": "Login", "user_token": user_token}
login_response = session.post(login_url, headers=headers, data=login_data, allow_redirects=False, timeout=REQUEST_TIMEOUT)

if login_response.status_code == 302 and "index.php" in login_response.headers.get("Location", ""):
    print("[✓] Login successful.\n")
else:
    print(f"[✗] Login failed! Status: {login_response.status_code}")
    exit(1)

# ==== 2. ZAP raporunu yükle ====
if not os.path.exists(zap_report_path):
    print(f"[!] ZAP report not found: {zap_report_path}")
    exit(1)
with open(zap_report_path, "r", encoding="utf-8") as file:
    zap_data = json.load(file)

results = []

# ==== 3. Zafiyetleri doğrula ====
print("Starting vulnerability validation...")
for site in zap_data.get("site", []):
    for alert in site.get("alerts", []):
        vuln_name = alert.get("name")
        for instance in alert.get("instances", []):
            method, uri = instance.get("method"), instance.get("uri")
            param, payload = instance.get("param"), instance.get("attack")

            if not all([method, uri]): continue

            result = {"vulnerability": vuln_name, "method": method, "url": uri, "param": param, "payload": payload}
            baseline_context = "Baseline request was not applicable or failed."
            attack_context = "Attack request failed."
            request_repr = ""

            try:
                # --- Baseline İsteği ---
                if method == "GET" and param:
                    parsed_uri = urllib.parse.urlparse(uri)
                    query_params = urllib.parse.parse_qs(parsed_uri.query, keep_blank_values=True)
                    if param in query_params:
                        query_params[param] = ['']
                    
                    baseline_query = urllib.parse.urlencode(query_params, doseq=True)
                    baseline_uri = parsed_uri._replace(query=baseline_query).geturl()
                    
                    print(f"[i] Sending BASELINE request to: {baseline_uri}")
                    baseline_res = session.get(baseline_uri, headers=headers, timeout=REQUEST_TIMEOUT)
                    baseline_context = get_response_context(baseline_res)

                # --- Saldırı İsteği ---
                print(f"[i] Sending ATTACK request to: {uri}")
                res = None
                if method == "GET":
                    res = session.get(uri, headers=headers, allow_redirects=True, timeout=REQUEST_TIMEOUT)
                    request_repr = f"GET {uri}"
                elif method == "POST":
                    data = {param: payload} if param and payload else {}
                    res = session.post(uri, data=data, headers=headers, allow_redirects=True, timeout=REQUEST_TIMEOUT)
                    request_repr = f"POST {uri}\nData: {data}"
                
                if res:
                    attack_context = get_response_context(res)
                    result["http_status"] = res.status_code
                    result["response_snippet"] = res.text[:10000]
                
                # --- AI Değerlendirmesi ---
                ai_prompt = create_ai_prompt_with_baseline(vuln_name, request_repr, baseline_context, attack_context)
                is_fp = evaluate_with_ai_model(ai_prompt)
                result["is_false_positive"] = is_fp
                print(f"[AI] '{vuln_name}' at '{uri}' → is_false_positive={is_fp}\n")

            except requests.exceptions.RequestException as e:
                print(f"[!] Network error for {uri}: {e}\n")
                result.update({"http_status": "NETWORK_ERROR", "response_snippet": str(e)})
            except Exception as e:
                print(f"[!] An unexpected error occurred for {uri}: {e}\n")
                result.update({"http_status": "UNEXPECTED_ERROR", "response_snippet": str(e)})

            results.append(result)

# ==== 4. Sonuçları kaydet ====
with open(output_raw, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

clean_results = [r for r in results if r.get("is_false_positive") is False]
with open(output_filtered, "w", encoding="utf-8") as f:
    json.dump(clean_results, f, indent=2, ensure_ascii=False)

print(f"\n[✓] Process completed.")
print(f" - Full results saved to: {output_raw}")
print(f" - Filtered results saved to: {output_filtered}")
