last_commit="$(cd /home/ubuntu-jenkins/Desktop/app-build/DVWA && git rev-parse HEAD^)"
echo "last commit is ${last_commit}"

docker run --rm \
  -v "/home/ubuntu-jenkins/Desktop/app-build/DVWA:/src" \
  -v "/home/ubuntu-jenkins/semgrep-rules:/rules:ro" \
  -v "/home/ubuntu-jenkins/Desktop:/output" \
  semgrep/semgrep semgrep ci \
  --config /rules \
  --metrics=off \
  --baseline-commit=${last_commit} \
  --verbose --json --output /output/semgrep_results.json

# echo 'Creating Github Issues of Semgrep Findings...'

# python3 /home/ubuntu-jenkins/Desktop/create_issues_semgrep.py

