
pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
    }

    environment {
        IMAGE_NAME = 'ev3-securedev'
        CONTAINER_NAME = 'ev3-securedev-app'
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Descargando codigo desde GitHub'

                git branch: 'main',
                    credentialsId: 'github-ev3-token',
                    url: 'https://github.com/Daaantiel/EV3-SecureDev.git'
            }
        }

        stage('Build') {
            steps {
                echo 'Construyendo imagen Docker'

                sh 'docker build -t ev3-securedev:${BUILD_NUMBER} .'
            }
        }

        stage('Test') {
            steps {
                echo 'Ejecutando pruebas automatizadas'

                sh '''
                    docker run --rm \
                      --entrypoint python \
                      ev3-securedev:${BUILD_NUMBER} \
                      -m unittest discover -s tests -t . -v
                '''
            }
        }

        stage('Deploy') {
            steps {
                echo 'Desplegando aplicacion Flask'

                sh '''
                    docker rm -f ev3-securedev-app \
                      >/dev/null 2>&1 || true

                    docker run -d \
                      --name ev3-securedev-app \
                      --restart unless-stopped \
                      -p 5000:5000 \
                      ev3-securedev:${BUILD_NUMBER}
                '''

                sh '''
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if docker exec ev3-securedev-app python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:5000/login', timeout=2).status == 200" >/dev/null 2>&1; then
                            echo 'Aplicacion desplegada correctamente'
                            exit 0
                        fi
                        sleep 2
                    done

                    docker logs ev3-securedev-app
                    exit 1
                '''
            }
        }

        stage('Security Scan - OWASP ZAP') {
            steps {
                echo 'Iniciando analisis automatizado OWASP ZAP'

                sh '''
                    mkdir -p zap-reports

                    docker network inspect ev3-zap-net \
                      >/dev/null 2>&1 || \
                      docker network create ev3-zap-net

                    docker network connect \
                      ev3-zap-net ev3-securedev-app

                    docker run --rm \
                      --network ev3-zap-net \
                      -v "${WORKSPACE}/zap-reports:/zap/wrk:rw" \
                      ghcr.io/zaproxy/zaproxy:stable \
                      zap-baseline.py \
                      -t http://ev3-securedev-app:5000/login \
                      -m 1 \
                      -I \
                      -r zap-report.html \
                      -J zap-report.json
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts(
                artifacts: 'zap-reports/*.html,zap-reports/*.json',
                allowEmptyArchive: true
            )
        }

        success {
            echo 'PIPELINE CI/CD Y ANALISIS ZAP COMPLETADOS'
        }

        failure {
            echo 'ERROR EN EL PIPELINE - Revisar Console Output'
        }
    }
}
