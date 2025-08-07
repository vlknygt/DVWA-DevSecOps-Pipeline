import json
import subprocess
import os
import random

# Semgrep sonuçlarının bulunduğu JSON dosyasının yolu
SEMGREP_RESULTS_FILE = '/home/ubuntu-jenkins/Desktop/semgrep_results.json' # Lütfen bu yolu güncelleyin

# Issue'ların oluşturulacağı GitHub projesinin dizini
# gh CLI bu dizinde çalıştırılacak
PROJECT_DIRECTORY = '/home/ubuntu-jenkins/Desktop/app-build/DVWA'


def ensure_labels_exist(required_labels, project_dir):
    """
    Gerekli etiketlerin GitHub deposunda var olduğundan emin olur.
    Eğer bir etiket yoksa, otomatik olarak oluşturur.
    """
    print("Ensuring all required labels exist...")
    try:
        # Komutları çalıştırmak için doğru dizine geç
        os.chdir(project_dir)
    except FileNotFoundError:
        print(f"Error: Project directory not found at {project_dir}")
        return False

    try:
        # Mevcut etiketleri al
        result = subprocess.run(
            ['gh', 'label', 'list', '--json', 'name'],
            check=True, capture_output=True, text=True
        )
        existing_labels_data = json.loads(result.stdout)
        existing_labels = {item['name'] for item in existing_labels_data}
        print(f"Found existing labels: {existing_labels}")

        # Ciddiyet seviyeleri için renkler tanımla
        severity_colors = {
            "CRITICAL": "b60205",
            "ERROR": "d93f0b",
            "WARNING": "fbca04",
            "INFO": "0e8a16",
            # Diğer seviyeler için varsayılan renk
            "default": "5319e7"
        }

        # Ana 'semgrep' etiketi için renk
        semgrep_color = "1d76db"

        for label in required_labels:
            if label not in existing_labels:
                print(f"Label '{label}' not found. Creating it...")
                
                # Etiket için renk seçimi
                if label.upper() in severity_colors:
                    color = severity_colors[label.upper()]
                elif label == 'semgrep':
                    color = semgrep_color
                else:
                    # Rastgele bir renk oluştur
                    color = f'{random.randint(0, 0xFFFFFF):06x}'

                create_cmd = [
                    'gh', 'label', 'create', label,
                    '--color', color,
                    '--description', f'Issue related to {label}'
                ]
                subprocess.run(create_cmd, check=True, capture_output=True, text=True)
                print(f"Successfully created label '{label}' with color '{color}'.")
        
        return True

    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"An error occurred while ensuring labels exist: {e}")
        if hasattr(e, 'stderr'):
            print(f"Stderr: {e.stderr}")
        return False


def create_github_issue(finding):
    """
    Verilen Semgrep bulgusu için bir GitHub issue oluşturur.
    """
    check_id = finding['check_id']
    file_path = finding['path']
    start_line = finding['start']['line']
    message = finding['extra']['message']
    severity = finding['extra']['severity']

    # Issue başlığını ve gövdesini oluştur
    title = f"Semgrep [{severity}]: {check_id} in {file_path}"

    body = f"""
### Semgrep Security Finding

**Rule ID:** `{check_id}`
**Severity:** {severity}
**File:** `{file_path}`
**Line:** {start_line}

---

### Description
{message}

---

**How to fix:**
Please review the code at the specified location and apply the necessary sanitization or code changes to mitigate the vulnerability.
"""

    # gh CLI komutunu kullanarak issue oluştur
    command = [
        'gh', 'issue', 'create',
        '--title', title,
        '--body', body,
        '--label', f"semgrep,{severity}"
    ]

    print(f"Creating issue for: {title}")
    try:
        os.chdir(PROJECT_DIRECTORY)
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Successfully created issue:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Failed to create issue.")
        print(f"Error: {e}")
        print(f"Stderr: {e.stderr}")
    except FileNotFoundError:
        print(f"Error: 'gh' command not found or project directory is incorrect.")


def main():
    """
    Ana fonksiyon. JSON dosyasını okur ve her bulgu için issue oluşturur.
    """
    if SEMGREP_RESULTS_FILE == '/path/to/your/semgrep_results.json':
        print("ERROR: Please update the SEMGREP_RESULTS_FILE variable in the script with the correct path.")
        return
        
    try:
        with open(SEMGREP_RESULTS_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Semgrep results file not found at {SEMGREP_RESULTS_FILE}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {SEMGREP_RESULTS_FILE}")
        return

    findings = data.get('results', [])
    if not findings:
        print("No findings found in the Semgrep report.")
        return

    # Gerekli tüm etiketleri topla (ana etiket + tüm ciddiyet seviyeleri)
    severities = {finding['extra']['severity'] for finding in findings}
    required_labels = ['semgrep'] + list(severities)

    # Etiketlerin var olduğundan emin ol, yoksa oluştur
    if not ensure_labels_exist(required_labels, PROJECT_DIRECTORY):
        print("Could not ensure labels exist. Aborting issue creation.")
        return

    print(f"\nFound {len(findings)} findings. Starting to create issues...")

    for finding in findings:
        create_github_issue(finding)
        print("-" * 40)


if __name__ == '__main__':
    main()
