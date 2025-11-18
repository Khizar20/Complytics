# Azure Deployment Quick Start

## TL;DR - What Azure Services You Need

### Essential Services:
1. **Azure Container Registry (ACR)** - Store Docker images
2. **Azure Container Apps** or **Azure App Service** - Run your containers
3. **Azure Cosmos DB for MongoDB API** - **This is where your data will be stored** (replaces local MongoDB)

### Optional but Recommended:
4. **Azure Key Vault** - Store secrets securely
5. **Azure Front Door** - Load balancing & CDN

## Data Storage Answer

**Your data will be stored in Azure Cosmos DB for MongoDB API**

- It's 100% compatible with MongoDB (uses same drivers)
- Fully managed by Azure
- Automatic backups, high availability
- Auto-scaling
- Global distribution available

**Migration**: Use `mongodump` from local MongoDB and `mongorestore` to Cosmos DB

## Quick Deployment Steps

### Option 1: Automated Script
```bash
# Make script executable (Linux/Mac)
chmod +x azure-deploy.sh

# Run deployment
./azure-deploy.sh
```

### Option 2: Manual Steps

1. **Create resources** (see `AZURE_DEPLOYMENT_GUIDE.md`)
2. **Build & push images** to ACR
3. **Deploy containers** to Container Apps
4. **Update environment variables** with Cosmos DB connection string
5. **Migrate data** from local MongoDB to Cosmos DB

## Cost Estimate

- **Small-Medium App**: ~$50-100/month
  - Container Apps: ~$20-50/month
  - Cosmos DB: ~$24/month (400 RU/s)
  - ACR: ~$5/month
  - Key Vault: ~$1/month

## Key Configuration Changes

### 1. MongoDB Connection String
Change from:
```
mongodb://mongo:27017
```

To:
```
mongodb://<account>:<key>@<account>.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb
```

### 2. CORS Origins
Add your Azure frontend URL to backend CORS settings

### 3. Frontend API URL
Update frontend to point to Azure backend URL

## Documentation Files

- **`AZURE_DEPLOYMENT_GUIDE.md`** - Complete detailed guide
- **`azure-deploy.sh`** - Automated deployment script
- **`azure-env-setup.md`** - Environment variables reference
- **`docker-compose.azure.example.yml`** - Example config for Cosmos DB

## Need Help?

See the full guide: `AZURE_DEPLOYMENT_GUIDE.md`



