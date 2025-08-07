import json
import os
import random
import requests

#TOKEN = os.getenv("GITHUB_TOKEN")
TOKEN = "SECRET"
if not TOKEN:
    raise EnvironmentError("GITHUB_TOKEN environment variable is required")

REPO_OWNER = "vlknygt"
REPO_NAME = "DVWA"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

JSON_FILE_PATH = '/home/ubuntu-jenkins/Desktop/ai-report/json-reports/filtered_results.json'
PROJECT_DIRECTORY = '/home/ubuntu-jenkins/Desktop/app-build/DVWA'


def ensure_labels_exist(required_labels):
    print("Ensuring all required labels exist via API...")
    resp = requests.get(f"{API_BASE}/labels", headers=HEADERS)
    resp.raise_for_status()
    existing = {lbl['name'] for lbl in resp.json()}
    print(f"Existing labels: {existing}")
    
    for label in required_labels:
        if label not in existing:
            color = "7e57c2" if label == "dast-zap" else f"{random.randint(0, 0xFFFFFF):06x}"
            data = {
                "name": label,
                "color": color,
                "description": f"Issue related to {label}"
            }
            r = requests.post(f"{API_BASE}/labels", headers=HEADERS, json=data)
            if r.status_code == 201:
                print(f"Created label '{label}' (color {color})")
            else:
                print(f"Failed to create label '{label}': {r.status_code} {r.text}")
                return False
    return True


def create_github_issue(vuln, labels):
    title = f"DAST Vulnerability: {vuln['vulnerability']}"
    body_lines = [
        "### Vulnerability Details (OWASP ZAP)",
        f"**Vulnerability:** {vuln.get('vulnerability', 'N/A')}",
        f"**Method:** {vuln.get('method', 'N/A')}",
        f"**URL:** `{vuln.get('url', 'N/A')}`",
        f"**Parameter:** `{vuln.get('param', 'N/A')}`",
        "",
        "**Payload:**",
        "```",
        vuln.get('payload', 'N/A'),
        "```",
        f"**HTTP Status:** {vuln.get('http_status', 'N/A')}",
        "",
        "### Response Snippet",
        "```html",
        vuln.get('response_snippet', 'N/A'),
        "```"
    ]

    # AI önerisi ekleme (mitigation)
    mitigation = vuln.get('mitigation')
    if mitigation:
        body_lines += [
            "",
            "### AI Recommendation",
            f"{mitigation}"
        ]

    issue_data = {
        "title": title,
        "body": "\n".join(body_lines),
        "labels": labels
    }
    r = requests.post(f"{API_BASE}/issues", headers=HEADERS, json=issue_data)
    if r.status_code == 201:
        number = r.json().get('number')
        print(f"Issue created: #{number} {title}")
    else:
        print(f"Error creating issue '{title}': {r.status_code} {r.text}")


def main():
    if not os.path.exists(JSON_FILE_PATH):
        print(f"Error: JSON file not found at '{JSON_FILE_PATH}'")
        return
    try:
        vulnerabilities = json.load(open(JSON_FILE_PATH, encoding='utf-8'))
    except Exception as e:
        print(f"Could not load JSON: {e}")
        return

    if not os.path.isdir(PROJECT_DIRECTORY):
        print(f"Error: project directory not found: {PROJECT_DIRECTORY}")
        return
    os.chdir(PROJECT_DIRECTORY)
    print(f"Changed cwd to: {os.getcwd()}")

    labels_to_create = ['dast-zap'] + list({
        vuln['vulnerability']
        for vuln in vulnerabilities
        if not vuln.get('is_false_positive')
    })

    if not ensure_labels_exist(labels_to_create):
        print("Label setup failed. Aborting.")
        return

    print(f"\nCreating issues for {len(vulnerabilities)} vulnerabilities...")
    for vuln in vulnerabilities:
        if not vuln.get('is_false_positive'):
            create_github_issue(vuln, ['dast-zap', vuln['vulnerability']])
        else:
            print(f"Skipping false positive: {vuln.get('vulnerability')}")

if __name__ == "__main__":
    main()

