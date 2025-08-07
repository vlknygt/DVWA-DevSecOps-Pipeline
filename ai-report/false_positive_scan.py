import json
import requests
from bs4 import BeautifulSoup
import os
from openai import OpenAI
import urllib.parse
import re

# ==== Config ====
use_gemini = True
test_mode = True  # True: Sadece 1 AI çağrısı yap, sonrakilerde cache kullan
base_url = "http://192.168.1.204:1235"
login_url = f"{base_url}/DVWA/login.php"
username = "admin"
password = "password"
zap_report_path = "/home/ubuntu-jenkins/Desktop/ai-report/zap_json.json"
output_raw = "/home/ubuntu-jenkins/Desktop/ai-report/json-reports/zap_results.json"
output_filtered = "/home/ubuntu-jenkins/Desktop/ai-report/json-reports/filtered_results.json"
REQUEST_TIMEOUT = 15
gemini_api_key = "SECRET"

os.makedirs(os.path.dirname(output_raw), exist_ok=True)

ai_client = OpenAI(
    api_key="dummy_value",
    base_url="http://192.168.1.200:12434/engines/llama.cpp/v1"
)

_ai_test_cache = None

def create_ai_prompt_with_baseline(vuln_type, request_str, baseline_context, attack_context):
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

Analysis Instructions:
1. Compare the 'Attack Context' to the 'Baseline Context'.
2. Determine if the vulnerability finding is a false positive.
3. If it's a real vulnerability, provide a short mitigation recommendation (e.g., "sanitize input using X", "use parameterized queries", etc).

Respond strictly in the following JSON format inside a code block:

json
{{
  "false_positive": true or false,
  "mitigation": "Your one-line fix or advice here (use 'N/A' if false positive)"
}}
"""

def extract_json(text):
    default_result = {"false_positive": False, "mitigation": "N/A"}
    try:
        print("[Gemini Yanıtı]:\n", text.strip())

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            json_text = match.group(1)
        else:
            json_text = text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:].strip("` \n")
            elif json_text.startswith("```"):
                json_text = json_text[3:].strip("` \n")

        json_text = json_text.replace("'", '"')
        json_text = re.sub(r'\btrue\b', 'true', json_text, flags=re.IGNORECASE)
        json_text = re.sub(r'\bfalse\b', 'false', json_text, flags=re.IGNORECASE)

        return json.loads(json_text)
    except Exception as e:
        print(f"[!] JSON parse error: {e}\n[!] Raw response:\n{text}")
        return default_result

def evaluate_with_ai_model(prompt):
    global _ai_test_cache
    default_result = {"false_positive": False, "mitigation": "N/A"}

    if test_mode:
        if _ai_test_cache is not None:
            print("[Test Mode] Returning cached AI result.")
            return _ai_test_cache
        print("[Test Mode] Making single AI call (real request allowed)...")
        try:
            if use_gemini:
                import google.generativeai as genai
                from google.api_core import exceptions as google_exceptions

                genai.configure(api_key=gemini_api_key)
                config = genai.types.GenerationConfig(temperature=0.0, top_k=1, max_output_tokens=128)
                model = genai.GenerativeModel("gemini-1.5-flash", generation_config=config)
                response = model.generate_content(prompt)
                _ai_test_cache = extract_json(response.text)
            else:
                response = ai_client.chat.completions.create(
                    model="ai/qwen3:0.6B-Q4_K_M",
                    messages=[
                        {"role": "system", "content": "You are a helpful security analyst AI assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                _ai_test_cache = extract_json(response.choices[0].message.content)

            return _ai_test_cache
        except Exception as e:
            print(f"[!] Test mode AI call failed: {e}")
            return default_result

    try:
        if use_gemini:
            import google.generativeai as genai
            from google.api_core import exceptions as google_exceptions

            genai.configure(api_key=gemini_api_key)
            config = genai.types.GenerationConfig(temperature=0.0, top_k=1, max_output_tokens=128)
            model = genai.GenerativeModel("gemini-1.5-flash", generation_config=config)
            response = model.generate_content(prompt)
            return extract_json(response.text)
        else:
            response = ai_client.chat.completions.create(
                model="ai/qwen3:0.6B-Q4_K_M",
                messages=[
                    {"role": "system", "content": "You are a helpful security analyst AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return extract_json(response.choices[0].message.content)
    except Exception as e:
        print(f"[!] Normal AI evaluation error: {e}")
        return default_result

def get_response_context(response):
    headers = json.dumps(dict(response.headers), indent=2)
    body = response.text[:10000]
    return f"Status Code: {response.status_code}\nHeaders:\n{headers}\n\nBody Snippet:\n{body}"

print("Attempting to log in to DVWA...")
session = requests.Session()
try:
    resp = session.get(login_url, timeout=REQUEST_TIMEOUT)
    soup = BeautifulSoup(resp.text, "html.parser")
    user_token = soup.find("input", {"name": "user_token"})["value"]
except Exception as e:
    print(f"[\u2717] Login failed: {e}")
    exit(1)

headers = {"Host": "192.168.1.204:1235", "User-Agent": "Mozilla/5.0", "Origin": base_url, "Referer": login_url}
session.cookies.set("security", "low")
login_data = {"username": username, "password": password, "Login": "Login", "user_token": user_token}
login_response = session.post(login_url, headers=headers, data=login_data, allow_redirects=False, timeout=REQUEST_TIMEOUT)

if login_response.status_code == 302 and "index.php" in login_response.headers.get("Location", ""):
    print("[\u2713] Login successful.\n")
else:
    print(f"[\u2717] Login failed! Status: {login_response.status_code}")
    exit(1)

if not os.path.exists(zap_report_path):
    print(f"[!] ZAP report not found: {zap_report_path}")
    exit(1)
with open(zap_report_path, "r", encoding="utf-8") as file:
    zap_data = json.load(file)

results = []
print("Starting vulnerability validation...")
for site in zap_data.get("site", []):
    for alert in site.get("alerts", []):
        vuln_name = alert.get("name")
        for instance in alert.get("instances", []):
            method, uri = instance.get("method"), instance.get("uri")
            param, payload = instance.get("param"), instance.get("attack")

            if not all([method, uri]):
                continue

            result = {"vulnerability": vuln_name, "method": method, "url": uri, "param": param, "payload": payload}
            baseline_context = "Baseline request was not applicable or failed."
            attack_context = "Attack request failed."
            request_repr = ""

            try:
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

                print(f"[i] Sending ATTACK request to: {uri}")
                res = None
                if method == "GET":
                    res = session.get(uri, headers=headers, timeout=REQUEST_TIMEOUT)
                    request_repr = f"GET {uri}"
                elif method == "POST":
                    data = {param: payload} if param and payload else {}
                    res = session.post(uri, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
                    request_repr = f"POST {uri}\nData: {data}"

                if res:
                    attack_context = get_response_context(res)
                    result["http_status"] = res.status_code
                    result["response_snippet"] = res.text[:10000]

                ai_prompt = create_ai_prompt_with_baseline(vuln_name, request_repr, baseline_context, attack_context)
                ai_result = evaluate_with_ai_model(ai_prompt)
                result["is_false_positive"] = ai_result.get("false_positive", False)
                result["mitigation"] = ai_result.get("mitigation", "N/A")

                print(f"[AI] {vuln_name} @ {uri} → FP: {result['is_false_positive']} | Mitigation: {result['mitigation']}\n")

            except requests.exceptions.RequestException as e:
                print(f"[!] Network error for {uri}: {e}")
                result.update({"http_status": "NETWORK_ERROR", "response_snippet": str(e)})
            except Exception as e:
                print(f"[!] Unexpected error for {uri}: {e}")
                result.update({"http_status": "UNEXPECTED_ERROR", "response_snippet": str(e)})

            results.append(result)

with open(output_raw, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

clean_results = [r for r in results if r.get("is_false_positive") is False]
with open(output_filtered, "w", encoding="utf-8") as f:
    json.dump(clean_results, f, indent=2, ensure_ascii=False)

print(f"\n[\u2713] Process completed.")
print(f" - Full results saved to: {output_raw}")
print(f" - Filtered results saved to: {output_filtered}")

