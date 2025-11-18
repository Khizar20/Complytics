# Jenkins Pipeline - Quick Start Guide

## 🚀 Quick Setup (5 Steps)

### 1. Install Jenkins
- Download from: https://www.jenkins.io/download/
- Or use Docker: `docker run -p 8080:8080 jenkins/jenkins:lts`

### 2. Install Required Plugins
Go to **Manage Jenkins** → **Manage Plugins** → Install:
- Docker Pipeline
- Credentials Binding
- Git (usually pre-installed)

### 3. Create Azure Service Principal

**Windows (PowerShell):**
```powershell
.\create-azure-service-principal.ps1
```

**Linux/Mac:**
```bash
chmod +x create-azure-service-principal.sh
./create-azure-service-principal.sh
```

**Or manually:**
```bash
az login
az account set --subscription "e7057718-109b-4459-9a1e-8acfe7595e3b"
az ad sp create-for-rbac --name "jenkins-complytics-sp" --role contributor --scopes /subscriptions/e7057718-109b-4459-9a1e-8acfe7595e3b/resourceGroups/complytics-rg
```

**Save the output:**
- `appId` (Client ID)
- `password` (Client Secret) ⚠️ Save this now!
- `tenant` (Tenant ID)

### 4. Configure Jenkins Credentials

Go to **Manage Jenkins** → **Manage Credentials** → **System** → **Global credentials**:

#### A. Docker Hub Credentials
- **Add Credentials**
- **Kind**: Username with password
- **Username**: `khizarahmed123`
- **Password**: Your Docker Hub password
- **ID**: `dockerhub-credentials`
- **Save**

#### B. Azure Service Principal
- **Add Credentials**
- **Kind**: Azure Service Principal (or Secret text if not available)
- **Subscription ID**: `e7057718-109b-4459-9a1e-8acfe7595e3b`
- **Client ID**: (from step 3)
- **Client Secret**: (from step 3)
- **Tenant ID**: (from step 3)
- **ID**: `azure-service-principal`
- **Save**

### 5. Create Pipeline Job

1. **New Item** → Name: `complytics-cicd` → **Pipeline** → **OK**
2. **Pipeline** → **Definition**: Pipeline script from SCM
3. **SCM**: Git
4. **Repository URL**: Your Git repo URL
5. **Script Path**: `Jenkinsfile` (or `Jenkinsfile.simple` for simpler version)
6. **Save**
7. **Build Now** 🚀

---

## 📋 Files Created

- `Jenkinsfile` - Full pipeline with build numbers and versioning
- `Jenkinsfile.simple` - Simplified version (recommended to start)
- `JENKINS_SETUP_GUIDE.md` - Detailed setup guide
- `create-azure-service-principal.sh` - Linux/Mac script
- `create-azure-service-principal.ps1` - Windows PowerShell script

---

## 🔧 Prerequisites on Jenkins Server

### Docker
```bash
# Linux
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins

# Windows
# Install Docker Desktop
```

### Azure CLI
```bash
# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from: https://aka.ms/installazurecliwindows
```

---

## 🎯 What the Pipeline Does

1. ✅ Checks out code from Git
2. ✅ Builds backend Docker image
3. ✅ Builds frontend Docker image
4. ✅ Pushes both to Docker Hub
5. ✅ Deploys backend to Azure Container Apps
6. ✅ Deploys frontend to Azure Container Apps
7. ✅ Verifies deployment

---

## 🔄 Auto-Trigger on Git Push (Optional)

### GitHub Webhook:
1. GitHub repo → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `http://your-jenkins-url/github-webhook/`
3. **Content type**: `application/json`
4. **Events**: Just the `push` event
5. **Save**

### Jenkins:
1. Pipeline job → **Configure**
2. **Build Triggers** → Check **GitHub hook trigger for GITScm polling**
3. **Save**

Now every push triggers automatic deployment! 🎉

---

## 🐛 Troubleshooting

### "Docker: permission denied"
```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

### "az: command not found"
- Install Azure CLI (see Prerequisites)
- Or use full path in Jenkinsfile

### "Azure login failed"
- Verify service principal credentials
- Check subscription ID is correct
- Ensure service principal has Contributor role

### "Docker login failed"
- Verify Docker Hub credentials
- Try using access token instead of password

---

## 📝 Customization

### Change Image Names
Edit `Jenkinsfile` environment section:
```groovy
DOCKERHUB_IMAGE_BACKEND = 'your-username/your-backend'
DOCKERHUB_IMAGE_FRONTEND = 'your-username/your-frontend'
```

### Change Azure Resources
Edit environment section:
```groovy
AZURE_RESOURCE_GROUP = 'your-resource-group'
AZURE_BACKEND_APP = 'your-backend-app'
AZURE_FRONTEND_APP = 'your-frontend-app'
```

### Add Build Number Tags
The full `Jenkinsfile` already includes build number tagging. The simple version uses `latest` only.

---

## ✅ Checklist

- [ ] Jenkins installed and running
- [ ] Required plugins installed
- [ ] Docker installed on Jenkins server
- [ ] Azure CLI installed on Jenkins server
- [ ] Azure Service Principal created
- [ ] Docker Hub credentials added to Jenkins
- [ ] Azure Service Principal credentials added to Jenkins
- [ ] Pipeline job created
- [ ] First build successful
- [ ] Webhook configured (optional)

---

## 🎉 You're Done!

Your CI/CD pipeline is now set up. Every time you push code to your repository (or manually trigger), Jenkins will:
- Build your Docker images
- Push them to Docker Hub
- Deploy to Azure automatically

No more manual deployments! 🚀

