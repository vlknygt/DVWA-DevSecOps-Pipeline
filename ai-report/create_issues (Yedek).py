import json
import os
import subprocess
import random

# JSON dosyasının tam yolu
JSON_FILE_PATH = '/home/ubuntu-jenkins/Desktop/ai-report/json-reports/filtered_results.json'

# Issue'ların oluşturulacağı GitHub projesinin dizini
PROJECT_DIRECTORY = '/home/ubuntu-jenkins/Desktop/app-build/DVWA'


def ensure_labels_exist(required_labels):
    """
    Gerekli etiketlerin GitHub deposunda var olduğundan emin olur.
    Eğer bir etiket yoksa, otomatik olarak oluşturur.
    """
    print("Ensuring all required labels exist...")
    try:
        # Mevcut etiketleri al
        result = subprocess.run(
            ['gh', 'label', 'list', '--json', 'name'],
            check=True, capture_output=True, text=True, encoding='utf-8'
        )
        existing_labels_data = json.loads(result.stdout)
        existing_labels = {item['name'] for item in existing_labels_data}
        print(f"Found existing labels: {existing_labels}")

        for label in required_labels:
            if label not in existing_labels:
                print(f"Label '{label}' not found. Creating it...")
                
                # Etiket için rastgele bir renk oluştur
                color = f'{random.randint(0, 0xFFFFFF):06x}'
                
                # dast-zap etiketi için sabit bir renk belirleyelim
                if label == 'dast-zap':
                    color = "7e57c2"

                create_cmd = [
                    'gh', 'label', 'create', label,
                    '--color', color,
                    '--description', f'Issue related to {label}'
                ]
                subprocess.run(create_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
                print(f"Successfully created label '{label}' with color '{color}'.")
        
        return True

    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"An error occurred while ensuring labels exist: {e}")
        if hasattr(e, 'stderr'):
            print(f"Stderr: {e.stderr}")
        return False


def create_github_issue(vulnerability_data, labels):
    """
    Verilen zafiyet verileri ve etiketlerle bir GitHub issue oluşturur.
    """
    title = f"DAST Vulnerability: {vulnerability_data['vulnerability']}"
    
    body_lines = [
        "### Vulnerability Details (OWASP ZAP)",
        f"**Vulnerability:** {vulnerability_data.get('vulnerability', 'N/A')}",
        f"**Method:** {vulnerability_data.get('method', 'N/A')}",
        f"**URL:** `{vulnerability_data.get('url', 'N/A')}`",
        f"**Parameter:** `{vulnerability_data.get('param', 'N/A')}`",
        "**Payload:**",
        "```",
        f"{vulnerability_data.get('payload', 'N/A')}",
        "```",
        f"**HTTP Status:** {vulnerability_data.get('http_status', 'N/A')}",
        "",
        "### Response Snippet",
        "```html",
        f"{vulnerability_data.get('response_snippet', 'N/A')}",
        "```"
    ]
    body = "\n".join(body_lines)
    
    command = [
        'gh', 'issue', 'create',
        '--title', title,
        '--body', body,
        '--label', ",".join(labels)  # Etiketleri virgülle ayırarak ekle
    ]
    
    try:
        print(f"Creating issue for: {title}")
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        print("Issue created successfully:")
        print(result.stdout)
    except FileNotFoundError:
        print("Error: 'gh' command not found. Please install the GitHub CLI and ensure it's in your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating GitHub issue for '{title}':")
        print(e.stderr)

def main():
    """
    Ana fonksiyon, JSON dosyasını okur, etiketleri kontrol eder ve her zafiyet için issue oluşturur.
    """
    if not os.path.exists(JSON_FILE_PATH):
        print(f"Error: JSON file not found at '{JSON_FILE_PATH}'")
        return

    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            vulnerabilities = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {e}")
        return
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return

    if not os.path.isdir(PROJECT_DIRECTORY):
        print(f"Error: Directory not found at '{PROJECT_DIRECTORY}'")
        return
        
    os.chdir(PROJECT_DIRECTORY)
    print(f"Changed directory to: {os.getcwd()}")
    
    # Gerekli tüm etiketleri topla: 'dast-zap' + tüm zafiyet türleri
    vulnerability_types = {
        vuln['vulnerability'] for vuln in vulnerabilities if not vuln.get('is_false_positive')
    }
    required_labels = ['dast-zap'] + list(vulnerability_types)
    
    # Etiketlerin var olduğundan emin ol, yoksa oluştur
    if not ensure_labels_exist(required_labels):
        print("Could not ensure labels exist. Aborting issue creation.")
        return

    print(f"\nFound {len(vulnerabilities)} potential vulnerabilities. Starting to create issues...")
    for vulnerability in vulnerabilities:
        if not vulnerability.get('is_false_positive'):
            # Her issue için ilgili etiketleri hazırla
            issue_labels = ['dast-zap', vulnerability['vulnerability']]
            create_github_issue(vulnerability, issue_labels)
        else:
            print(f"Skipping false positive: {vulnerability.get('vulnerability')}")

if __name__ == '__main__':
    main()
