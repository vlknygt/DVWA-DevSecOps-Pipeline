import json
import subprocess
import os

# Snyk sonuçlarının bulunduğu JSON dosyasının yolu
SNYK_RESULTS_FILE = '/home/ubuntu-jenkins/Desktop/snyk-sca/snyk_results.json'

# Issue'ların oluşturulacağı GitHub projesinin dizini
# gh CLI bu dizinde çalıştırılacak
PROJECT_DIRECTORY = '/home/ubuntu-jenkins/Desktop/app-build/DVWA'

def create_github_issue(vulnerability_details):
    """
    Verilen güvenlik açığı detayları için bir GitHub issue oluşturur.
    """
    # Issue başlığını ve gövdesini oluştur
    title = f"Snyk Vulnerability: {vulnerability_details['title']} in {vulnerability_details['packageName']}"

    # CVE bilgilerini al, yoksa 'N/A' olarak ayarla
    cve_list = vulnerability_details['identifiers'].get('CVE', [])
    cve_str = ', '.join(cve_list) if cve_list else 'N/A'

    # Etkilenen yolları listele
    affected_paths = "\n".join([f"- `{' > '.join(path)}`" for path in vulnerability_details['from_paths']])

    # Düzeltme yolu (upgrade path)
    remediation = f"Upgrade `{vulnerability_details['packageName']}` to version `{vulnerability_details['fixedIn'][0]}` or higher." if vulnerability_details.get('fixedIn') else "No direct upgrade path available. Please check the description."

    body = f"""
### Snyk Vulnerability Report

**Vulnerability:** {vulnerability_details['title']}
**Severity:** {vulnerability_details['severity'].capitalize()}
**Vulnerable Package:** `{vulnerability_details['packageName']}`
**Vulnerable Version:** `{vulnerability_details['version']}`
**Snyk ID:** `{vulnerability_details['id']}`
**CVE:** {cve_str}

---

### Description
{vulnerability_details['description']}

---

### Affected Paths
This vulnerability was found in the following dependency paths:
{affected_paths}

---

### Remediation
{remediation}
"""

    # Komutu çalıştıracağımız dizine geç
    try:
        os.chdir(PROJECT_DIRECTORY)
        print(f"Changed directory to {PROJECT_DIRECTORY}")
    except FileNotFoundError:
        print(f"Error: Project directory not found at {PROJECT_DIRECTORY}")
        return

    # gh CLI komutunu kullanarak issue oluştur
    command = [
        'gh', 'issue', 'create',
        '--title', title,
        '--body', body
    ]

    print(f"Creating issue for: {title}")
    try:
        # Komutu çalıştır ve çıktıyı yakala
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Successfully created issue:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Failed to create issue.")
        print(f"Error: {e}")
        print(f"Stderr: {e.stderr}")
    except FileNotFoundError:
        print("Error: 'gh' command not found. Make sure the GitHub CLI is installed and in your PATH.")


def main():
    """
    Ana fonksiyon. JSON dosyasını okur ve her güvenlik açığı için issue oluşturur.
    """
    try:
        with open(SNYK_RESULTS_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Snyk results file not found at {SNYK_RESULTS_FILE}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {SNYK_RESULTS_FILE}")
        return

    vulnerabilities = data.get('vulnerabilities', [])
    if not vulnerabilities:
        print("No vulnerabilities found in the report.")
        return

    # Aynı ID'ye sahip zafiyetleri grupla
    unique_vulnerabilities = {}
    for vuln in vulnerabilities:
        vuln_id = vuln['id']
        if vuln_id not in unique_vulnerabilities:
            unique_vulnerabilities[vuln_id] = vuln
            unique_vulnerabilities[vuln_id]['from_paths'] = [vuln['from']]
        else:
            # Daha önce eklenmiş zafiyete yeni yolu ekle
            unique_vulnerabilities[vuln_id]['from_paths'].append(vuln['from'])

    print(f"Found {len(unique_vulnerabilities)} unique vulnerabilities. Creating issues...")

    for vuln_id, vuln_details in unique_vulnerabilities.items():
        create_github_issue(vuln_details)
        print("-" * 40)


if __name__ == '__main__':
    main()
