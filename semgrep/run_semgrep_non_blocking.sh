last_commit="$(cd /home/ubuntu-jenkins/Desktop/app-build/DVWA && git rev-parse HEAD^)"
echo "last commit is ${last_commit}"

docker run --rm \
  -v "/home/ubuntu-jenkins/Desktop/app-build/DVWA:/src" \
  -v "/home/ubuntu-jenkins/semgrep-rules-non-blocking:/rules:ro" \
  -v "/home/ubuntu-jenkins/Desktop/semgrep:/output" \
  semgrep/semgrep semgrep scan \
  --config /rules \
  --metrics=off \
  --baseline-commit=${last_commit} \
  --verbose --json --output /output/semgrep_results_non_blocking.json
  
