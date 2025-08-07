rm -f /home/ubuntu-jenkins/Desktop/ai-report/zap_json.json
cp /home/ubuntu-jenkins/Desktop/zap-report/* /home/ubuntu-jenkins/Desktop/ai-report/zap_json.json
rm -rf /home/ubuntu-jenkins/Desktop/ai-report/json-reports/*

source /home/ubuntu-jenkins/Desktop/ai-report/venv/bin/activate
python3 -u /home/ubuntu-jenkins/Desktop/ai-report/false_positive_scan.py
