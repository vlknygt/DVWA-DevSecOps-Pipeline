pipeline {
    agent any 
    stages {
        stage('Clone the repo') {
            steps {
                cleanWs()
                checkout scmGit(branches: [[name: '*/master']], extensions: [], userRemoteConfigs: [[credentialsId: 'dvwa', url: 'https://github.com/vlknygt/DVWA.git']])
                sh 'rm -rf DVWA'
                sh 'git clone https://github.com/vlknygt/DVWA.git'
            }
        }
        stage('Send App to Local VM') {
            steps {
                echo 'Zip DVWA Folder'
                sh 'rm -f DVWA.zip'
                sh 'zip -r DVWA.zip DVWA'
                
                echo 'Sending App to Local VM..'
                sh 'scp DVWA.zip ubuntu-jenkins@192.168.1.204:/home/ubuntu-jenkins/Desktop/app-build'
                sh 'ssh ubuntu-jenkins@192.168.1.204 rm -rf /home/ubuntu-jenkins/Desktop/app-build/DVWA'
                sh 'ssh ubuntu-jenkins@192.168.1.204 unzip -o /home/ubuntu-jenkins/Desktop/app-build/DVWA.zip -d /home/ubuntu-jenkins/Desktop/app-build/'
            }
        }
        stage('Scan the code using DAST tool (OWASP ZAP)') {
            steps {
                echo 'Starting ZAP...'
                sh 'ssh ubuntu-jenkins@192.168.1.204 /home/ubuntu-jenkins/Desktop/zaptest.sh'
                echo 'ZAP Test Ended! Report saved!'
            }
        }
        stage('Detecting False Positive Findings with AI') {
            steps {
                sh 'ssh ubuntu-jenkins@192.168.1.204 /home/ubuntu-jenkins/Desktop/ai-report/run_ai_tests.sh'
                echo 'Report with true positive findings saved!'
            }
        }
        stage('Opening Github Issues for DAST Scan Results') {
            steps {
                sh 'ssh ubuntu-jenkins@192.168.1.204 python3 -u /home/ubuntu-jenkins/Desktop/ai-report/create_issues.py'
                echo 'Github Issues created on the repository for DAST Scan Results'
            }
        }
        stage('Software Component Analysis (Synk)') {
            steps {
                sh 'ssh ubuntu-jenkins@192.168.1.204 /home/ubuntu-jenkins/Desktop/snyk-sca/run_snyk.sh'
                echo 'SCA Completed and Github Issues Created If a Vulnerability Exists!'
            }
        }
        stage('Scan the code using SAST tool (Semgrep) - Blocking Rules') {
          steps {
            script {
              boolean vuln_found = false
              try {
                echo 'Scanning the code...'
                sh 'ssh ubuntu-jenkins@192.168.1.204 /home/ubuntu-jenkins/Desktop/run_semgrep.sh'
                echo 'Semgrep SAST Scan Completed. There is not any finding!'
              } catch (Exception err) {
                echo 'Semgrep found security issues on the Code! Saving the findings!'
                sh 'ssh ubuntu-jenkins@192.168.1.204 python3 -u /home/ubuntu-jenkins/Desktop/create_issues_semgrep.py'
                vuln_found = true
              }

              if(vuln_found){
                error('Semgrep detected security issue on the code!')
              }
            }
          }
        }
        stage('Scan the code using SAST tool (Semgrep) - Non Blocking Rules') {
            steps {
                sh 'ssh ubuntu-jenkins@192.168.1.204 /home/ubuntu-jenkins/Desktop/semgrep/run_semgrep_non_blocking.sh'
                echo 'Scan the code using SAST tool (Semgrep) - Non Blocking Rules - Completed!'
            }
        }
         stage('Creating Github Issues for Non Blocking Findings') {
            steps {
                sh 'ssh ubuntu-jenkins@192.168.1.204 python3 -u /home/ubuntu-jenkins/Desktop/semgrep/create_issues_semgrep_non_blocking.py'
                echo 'Creating Github Issues for Non Blocking Findings - Completed!'
            }
        }
         stage('Build the Application') {
            steps {
                echo 'Building application via Dockerfile'
                sh 'ssh ubuntu-jenkins@192.168.1.204 docker build -f /home/ubuntu-jenkins/Desktop/app-build/Dockerfile.app -t dvwa /home/ubuntu-jenkins/Desktop/app-build'
                echo 'dvwa image created..'
            }
        }
        stage('Send App image to App VM and Run') {
            steps {
                echo 'Saving image as tar file'
                sh 'ssh ubuntu-jenkins@192.168.1.204 /home/ubuntu-jenkins/Desktop/send-image.sh'
                
                echo 'Run Application on Application VM'
                sh 'ssh volkan@192.168.1.203 dockerstop'
                sh 'ssh volkan@192.168.1.203 docker compose -f /home/volkan/Desktop/docker-compose.yaml up -d'
            }
        }
    }
}
