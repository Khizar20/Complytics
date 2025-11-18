pipeline {
    agent any
    
    environment {
        // Docker Hub credentials (stored in Jenkins credentials)
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        DOCKERHUB_USERNAME = credentials('dockerhub-username')
        DOCKERHUB_IMAGE_BACKEND = 'khizarahmed123/complytics-backend'
        DOCKERHUB_IMAGE_FRONTEND = 'khizarahmed123/complytics-frontend'
        
        // Azure credentials (stored in Jenkins credentials)
        AZURE_CREDENTIALS = credentials('azure-service-principal')
        AZURE_SUBSCRIPTION_ID = 'e7057718-109b-4459-9a1e-8acfe7595e3b'
        AZURE_RESOURCE_GROUP = 'complytics-rg'
        AZURE_BACKEND_APP = 'complytics-backend'
        AZURE_FRONTEND_APP = 'complytics-frontend'
        
        // Image tags
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        IMAGE_TAG_LATEST = "latest"
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code from repository...'
                checkout scm
            }
        }
        
        stage('Build Backend Image') {
            steps {
                echo 'Building backend Docker image...'
                script {
                    docker.build("${DOCKERHUB_IMAGE_BACKEND}:${IMAGE_TAG}")
                    docker.build("${DOCKERHUB_IMAGE_BACKEND}:${IMAGE_TAG_LATEST}")
                }
            }
        }
        
        stage('Build Frontend Image') {
            steps {
                echo 'Building frontend Docker image...'
                script {
                    docker.build("${DOCKERHUB_IMAGE_FRONTEND}:${IMAGE_TAG}")
                    docker.build("${DOCKERHUB_IMAGE_FRONTEND}:${IMAGE_TAG_LATEST}")
                }
            }
        }
        
        stage('Push to Docker Hub') {
            steps {
                echo 'Pushing images to Docker Hub...'
                script {
                    // Login to Docker Hub
                    sh """
                        echo ${DOCKERHUB_CREDENTIALS_PSW} | docker login -u ${DOCKERHUB_CREDENTIALS_USR} --password-stdin
                    """
                    
                    // Push backend images
                    sh "docker push ${DOCKERHUB_IMAGE_BACKEND}:${IMAGE_TAG}"
                    sh "docker push ${DOCKERHUB_IMAGE_BACKEND}:${IMAGE_TAG_LATEST}"
                    
                    // Push frontend images
                    sh "docker push ${DOCKERHUB_IMAGE_FRONTEND}:${IMAGE_TAG}"
                    sh "docker push ${DOCKERHUB_IMAGE_FRONTEND}:${IMAGE_TAG_LATEST}"
                }
            }
        }
        
        stage('Deploy to Azure - Backend') {
            steps {
                echo 'Deploying backend to Azure Container Apps...'
                script {
                    withCredentials([azureServicePrincipal(credentialsId: 'azure-service-principal')]) {
                        sh """
                            az login --service-principal \
                                -u \${AZURE_CLIENT_ID} \
                                -p \${AZURE_CLIENT_SECRET} \
                                --tenant \${AZURE_TENANT_ID}
                            
                            az account set --subscription ${AZURE_SUBSCRIPTION_ID}
                            
                            az containerapp update \
                                --name ${AZURE_BACKEND_APP} \
                                --resource-group ${AZURE_RESOURCE_GROUP} \
                                --image ${DOCKERHUB_IMAGE_BACKEND}:${IMAGE_TAG_LATEST}
                        """
                    }
                }
            }
        }
        
        stage('Deploy to Azure - Frontend') {
            steps {
                echo 'Deploying frontend to Azure Container Apps...'
                script {
                    withCredentials([azureServicePrincipal(credentialsId: 'azure-service-principal')]) {
                        sh """
                            az containerapp update \
                                --name ${AZURE_FRONTEND_APP} \
                                --resource-group ${AZURE_RESOURCE_GROUP} \
                                --image ${DOCKERHUB_IMAGE_FRONTEND}:${IMAGE_TAG_LATEST}
                        """
                    }
                }
            }
        }
        
        stage('Verify Deployment') {
            steps {
                echo 'Verifying deployment...'
                script {
                    withCredentials([azureServicePrincipal(credentialsId: 'azure-service-principal')]) {
                        sh """
                            echo "Backend URL:"
                            az containerapp show \
                                --name ${AZURE_BACKEND_APP} \
                                --resource-group ${AZURE_RESOURCE_GROUP} \
                                --query "properties.configuration.ingress.fqdn" -o tsv
                            
                            echo "Frontend URL:"
                            az containerapp show \
                                --name ${AZURE_FRONTEND_APP} \
                                --resource-group ${AZURE_RESOURCE_GROUP} \
                                --query "properties.configuration.ingress.fqdn" -o tsv
                        """
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo 'Pipeline completed successfully!'
            // Optional: Send notification (email, Slack, etc.)
        }
        failure {
            echo 'Pipeline failed!'
            // Optional: Send failure notification
        }
        always {
            // Cleanup Docker images to save space
            sh 'docker system prune -f'
        }
    }
}

