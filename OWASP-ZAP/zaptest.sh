echo "Closing the old application (if exists)"
docker compose -f /home/ubuntu-jenkins/Desktop/docker-compose.yaml down
echo "Building latest application for test"
docker build -f /home/ubuntu-jenkins/Desktop/app-build/Dockerfile.app -t dvwa-preprod /home/ubuntu-jenkins/Desktop/app-build
echo "Starting the latest application"
docker compose -f /home/ubuntu-jenkins/Desktop/docker-compose.yaml up -d

while ! nc -z localhost 1235; do
  echo "Waiting for port 1235 to open..."
  sleep 1
done

echo "Port 1235 is now open! Application Started!"

echo "Starting OWASP ZAP Automated Testing..."
rm -rf /home/ubuntu-jenkins/Desktop/zap-report/*
zap.sh  -cmd -autorun zaptest.yaml -port 8085

echo "OWASP ZAP Test Finished!"

# echo "Closing Application..."
# docker compose -f /home/ubuntu-jenkins/Desktop/docker-compose.yaml down
