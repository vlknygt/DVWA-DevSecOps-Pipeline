rm -f snyk_results.json

docker run --rm -it -e SNYK_TOKEN=fb3f43a3-97ab-4298-aca1-432b020ebac2 -v /home/ubuntu-jenkins/Desktop/app-build/DVWA:/project snyk/snyk:linux snyk test --file=/project/vulnerabilities/api/composer.lock --package-manager=composer --json  > snyk_results.json

cat snyk_results.json

python3 -u /home/ubuntu-jenkins/Desktop/snyk-sca/create_issues_snyk.py
