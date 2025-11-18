# Jenkins CI/CD Pipeline Setup Guide

This guide will help you set up a Jenkins pipeline to automatically build, push, and deploy your Complytics application to Azure.

## Prerequisites

1. **Jenkins Server** (installed and running)
   - Can be on a local machine, VM, or cloud instance
   - Jenkins 2.400+ recommended

2. **Required Jenkins Plugins:**
   - Docker Pipeline
   - Azure CLI
   - Credentials Binding
   - Git

3. **Docker** installed on Jenkins server

4. **Azure CLI** installed on Jenkins server

5. **Docker Hub account** (already have)

6. **Azure Service Principal** (for automated deployments)

---

## Step 1: Install Jenkins Plugins

1. Go to **Jenkins Dashboard** → **Manage Jenkins** → **Manage Plugins**
2. Install the following plugins:
   - **Docker Pipeline**
   - **Azure CLI** (or use shell commands)
   - **Credentials Binding**
   - **Git** (usually pre-installed)

3. Restart Jenkins after installation

---

## Step 2: Create Azure Service Principal

You need an Azure Service Principal for Jenkins to authenticate with Azure.

### Option A: Using Azure Portal

1. Go to Azure Portal → **Azure Active Directory** → **App registrations**
2. Click **+ New registration**
3. Name: `jenkins-complytics-sp`
4. Click **Register**
5. Note down:
   - **Application (client) ID**
   - **Directory (tenant) ID**

6. Go to **Certificates & secrets** → **+ New client secret**
7. Create a secret and **copy it immediately** (you won't see it again)

8. Go to **Subscriptions** → Your subscription → **Access control (IAM)**
9. Click **+ Add** → **Add role assignment**
10. Role: **Contributor** (or **Container Apps Contributor**)
11. Assign access to: **Service principal**
12. Select your service principal
13. Click **Save**

### Option B: Using Azure CLI (if you have it)

```bash
az login
az account set --subscription "e7057718-109b-4459-9a1e-8acfe7595e3b"

az ad sp create-for-rbac \
  --name "jenkins-complytics-sp" \
  --role contributor \
  --scopes /subscriptions/e7057718-109b-4459-9a1e-8acfe7595e3b/resourceGroups/complytics-rg

# Note down:
# - appId (client ID)
# - password (client secret)
# - tenant (tenant ID)
```

---

## Step 3: Configure Jenkins Credentials

### 3.1 Docker Hub Credentials

1. Go to **Jenkins Dashboard** → **Manage Jenkins** → **Manage Credentials**
2. Click **System** → **Global credentials** → **Add Credentials**
3. Configure:
   - **Kind**: Username with password
   - **Scope**: Global
   - **Username**: Your Docker Hub username (`khizarahmed123`)
   - **Password**: Your Docker Hub password or access token
   - **ID**: `dockerhub-credentials`
   - **Description**: Docker Hub credentials for Complytics

4. Click **OK**

### 3.2 Docker Hub Username (Separate)

1. Add another credential:
   - **Kind**: Secret text
   - **Scope**: Global
   - **Secret**: `khizarahmed123` (your Docker Hub username)
   - **ID**: `dockerhub-username`
   - **Description**: Docker Hub username

### 3.3 Azure Service Principal

1. Add credential:
   - **Kind**: Azure Service Principal
   - **Scope**: Global
   - **Subscription ID**: `e7057718-109b-4459-9a1e-8acfe7595e3b`
   - **Client ID**: (from Step 2)
   - **Client Secret**: (from Step 2)
   - **Tenant ID**: (from Step 2)
   - **ID**: `azure-service-principal`
   - **Description**: Azure Service Principal for Complytics deployment

2. Click **OK**

---

## Step 4: Install Docker on Jenkins Server

If Docker is not installed on your Jenkins server:

### Windows (Jenkins on Windows):
```powershell
# Install Docker Desktop for Windows
# Or use WSL2 with Docker
```

### Linux (Jenkins on Linux):
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add Jenkins user to docker group
sudo usermod -aG docker jenkins

# Restart Jenkins
sudo systemctl restart jenkins
```

### Verify Docker:
```bash
docker --version
docker ps
```

---

## Step 5: Install Azure CLI on Jenkins Server

### Windows:
Download and install from: https://aka.ms/installazurecliwindows

### Linux:
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Verify:
```bash
az --version
```

---

## Step 6: Create Jenkins Pipeline

### Option A: Pipeline from SCM (Recommended)

1. Go to **Jenkins Dashboard** → **New Item**
2. Enter name: `complytics-cicd`
3. Select **Pipeline**
4. Click **OK**

5. Configure:
   - **Description**: Complytics CI/CD Pipeline
   - **Pipeline** → **Definition**: Pipeline script from SCM
   - **SCM**: Git
   - **Repository URL**: Your Git repository URL
   - **Credentials**: (if private repo)
   - **Branches to build**: `*/main` or `*/master`
   - **Script Path**: `Jenkinsfile`

6. Click **Save**

### Option B: Pipeline Script (Direct)

1. Create new Pipeline job
2. **Pipeline** → **Definition**: Pipeline script
3. Copy the entire `Jenkinsfile` content into the script box
4. Click **Save**

---

## Step 7: Run the Pipeline

1. Go to your pipeline job
2. Click **Build Now**
3. Watch the build progress in **Console Output**

---

## Step 8: Configure Webhooks (Optional - Auto-trigger on Git Push)

### GitHub:

1. Go to your GitHub repository → **Settings** → **Webhooks**
2. Click **Add webhook**
3. Configure:
   - **Payload URL**: `http://your-jenkins-url/github-webhook/`
   - **Content type**: `application/json`
   - **Events**: Just the `push` event
4. Click **Add webhook**

### In Jenkins:

1. Go to your pipeline job → **Configure**
2. **Build Triggers** → Check **GitHub hook trigger for GITScm polling**
3. Click **Save**

Now, every push to your repository will automatically trigger the pipeline!

---

## Pipeline Stages Explained

1. **Checkout**: Gets code from Git repository
2. **Build Backend Image**: Builds Docker image for backend
3. **Build Frontend Image**: Builds Docker image for frontend
4. **Push to Docker Hub**: Pushes both images to Docker Hub
5. **Deploy to Azure - Backend**: Updates Azure Container App with new backend image
6. **Deploy to Azure - Frontend**: Updates Azure Container App with new frontend image
7. **Verify Deployment**: Shows the deployed URLs

---

## Troubleshooting

### Docker Permission Denied
```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

### Azure CLI Not Found
- Ensure Azure CLI is installed and in PATH
- Or use full path: `/usr/bin/az` or `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`

### Docker Login Fails
- Verify Docker Hub credentials are correct
- Check if using access token instead of password

### Azure Deployment Fails
- Verify Service Principal has correct permissions
- Check subscription ID is correct
- Ensure resource group and container app names match

### Build Fails
- Check Docker is running: `docker ps`
- Verify Dockerfile paths are correct
- Check disk space: `df -h` (Linux) or check disk space (Windows)

---

## Customizing the Pipeline

### Add Environment Variables

Edit `Jenkinsfile` and add to `environment` block:
```groovy
environment {
    CUSTOM_VAR = 'value'
}
```

### Deploy to Different Environments

Add parameters:
```groovy
parameters {
    choice(
        name: 'ENVIRONMENT',
        choices: ['dev', 'staging', 'production'],
        description: 'Deployment environment'
    )
}
```

### Add Notifications

Add to `post` block:
```groovy
post {
    success {
        emailext(
            subject: "Pipeline Success: ${env.JOB_NAME}",
            body: "Build ${env.BUILD_NUMBER} succeeded!",
            to: "your-email@example.com"
        )
    }
}
```

---

## Security Best Practices

1. **Never commit credentials** to Git
2. **Use Jenkins credentials** for all secrets
3. **Rotate service principal secrets** regularly
4. **Limit service principal permissions** to minimum required
5. **Use separate service principals** for different environments
6. **Enable audit logging** in Jenkins

---

## Next Steps

1. ✅ Set up Jenkins server
2. ✅ Install required plugins
3. ✅ Create Azure Service Principal
4. ✅ Configure Jenkins credentials
5. ✅ Create pipeline job
6. ✅ Test pipeline
7. ✅ Set up webhooks (optional)
8. ✅ Monitor deployments

---

## Support

If you encounter issues:
1. Check Jenkins console output for detailed error messages
2. Verify all credentials are correctly configured
3. Ensure Docker and Azure CLI are properly installed
4. Check Azure portal for deployment status

