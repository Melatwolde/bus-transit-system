pipeline {
    agent any

    stages {
        stage('Checkout Code') {
            steps {
                // Checks out code from the GitHub repository
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Unit & Integration Tests (Coverage Gate)') {
            steps {
                // Enforces at least 80% branch coverage across core business logic
                sh '''
                    pytest tests/unit tests/integration \
                        --cov=src \
                        --cov-branch \
                        --cov-report=term-missing \
                        --cov-fail-under=80
                '''
            }
        }

        stage('System E2E Selenium Tests') {
            steps {
                // Runs headless Selenium browser tests
                sh 'pytest tests/system/test_e2e_booking.py'
            }
        }
    }

    post {
        always {
            cleanWs() // Keeps workspace clean between runs
        }
        success {
            echo "Jenkins Build Status: GREEN - All suites passed and coverage gate met!"
        }
        failure {
            echo "Jenkins Build Status: RED - Defect detected or coverage dropped below 80%!"
        }
    }
}