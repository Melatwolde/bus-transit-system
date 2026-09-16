pipeline {
    agent any

    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    ./venv/bin/python -m pip install --upgrade pip
                    ./venv/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Unit & Integration Tests (Coverage Gate)') {
            steps {
                sh '''
                    PYTHONPATH=. ./venv/bin/pytest tests/integration/test_app_endpoints.py \
                        -W ignore::DeprecationWarning \
                        --cov=src.app \
                        --cov-branch \
                        --cov-report=term-missing \
                        --cov-fail-under=80
                '''
            }
        }

        stage('System E2E Selenium Tests') {
            steps {
                sh 'echo "E2E Stage Ready"'
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
