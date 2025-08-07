import os
import json
import requests

# --- Ayarlar ---
#TOKEN = os.getenv("GITHUB_TOKEN")
TOKEN = "SECRET"
OWNER = "vlknygt"
REPO = "DVWA"
BASE_API = f"https://api.github.com/repos/{OWNER}/{REPO}"

SEMGRP_FILE = '/home/ubuntu-jenkins/Desktop/semgrep_results.json'

# --- Etiket kontrolü ---
def ensure_labels_exist(labels):
    url = f"{BASE_API}/labels"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(url, headers=headers)

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        print("Label listesi alınamadı:", e, response.text)
        return

    existing = response.json()
    if not isinstance(existing, list):
        print("Beklenmeyen yanıt formatı:", existing)
        return

    names = {l["name"] for l in existing}

    colors = {
        "CRITICAL": "b60205",
        "ERROR": "d93f0b",
        "WARNING": "fbca04",
        "INFO": "0e8a16",
        "semgrep": "1d76db"
    }

    for label in labels:
        if label not in names:
            payload = {"name": label, "color": colors.get(label, "5319e7")}
            r = requests.post(url, json=payload, headers=headers)
            if r.status_code != 201:
                print("Label oluşturulamadı:", label, r.text)

# --- Son commit SHA ---
def get_master_sha():
    url = f"{BASE_API}/commits/master"
    r = requests.get(url, headers={"Authorization": f"Bearer {TOKEN}"})
    r.raise_for_status()
    return r.json()["sha"]

# --- Issue oluştur ---
def create_issue(finding, commit_sha):
    path = finding['path']
    line = finding['start']['line']
    cid = finding['check_id']
    sev = finding['extra']['severity']
    msg = finding['extra']['message']

    permalink = f"https://github.com/{OWNER}/{REPO}/blob/{commit_sha}/{path}#L{line}"

    title = f"Semgrep [{sev}]: {cid} in {path}"
    body = (
        f"### Semgrep Finding\n\n"
        f"**Rule ID:** `{cid}`\n"
        f"**Severity:** {sev}\n"
        f"**File:** `{path}`\n"
        f"**Line:** {line}\n\n"
        f"**Permalink:** {permalink}\n\n"
        f"---\n\n{msg}\n"
    )
    payload = {"title": title, "body": body, "labels": ["semgrep", sev]}
    r = requests.post(f"{BASE_API}/issues", json=payload,
                      headers={"Authorization": f"Bearer {TOKEN}",
                               "Accept": "application/vnd.github+json"})
    if r.status_code == 201:
        print("Issue created:", r.json()["html_url"])
    else:
        print("Issue error:", r.status_code, r.text)

# --- Main ---
def main():
    try:
        with open(SEMGRP_FILE) as f:
            data = json.load(f)
    except Exception as e:
        return print("JSON load error:", e)

    findings = data.get("results", [])
    if not findings:
        return print("No findings.")

    labels = {"semgrep"} | {f["extra"]["severity"] for f in findings}
    ensure_labels_exist(labels)
    sha = get_master_sha()

    for f in findings:
        create_issue(f, sha)

if __name__ == "__main__":
    main()

