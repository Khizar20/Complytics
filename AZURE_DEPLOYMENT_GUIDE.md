# Azure Deployment Guide for Complytics

This guide explains how to containerize and deploy your Complytics application on Azure, including data storage migration from local MongoDB to Azure Cosmos DB.

## Azure Services Overview

### Required Services

1. **Azure Container Registry (ACR)**
   - Purpose: Store and manage your Docker container images
   - Why: Private registry for your containerized applications
   - Cost: Pay-as-you-go, ~$0.167/day for Basic tier

2. **Azure Container Apps** (Recommended) OR **Azure App Service**
   - **Azure Container Apps**: Best for microservices, auto-scaling, serverless containers
   - **Azure App Service**: Simpler, good for traditional web apps
   - Purpose: Host your containerized backend and frontend
   - Why: Fully managed container hosting with auto-scaling

3. **Azure Cosmos DB for MongoDB API**
   - Purpose: Replace local MongoDB with managed MongoDB-compatible database
   - Why: Fully managed, globally distributed, auto-scaling, 99.999% availability
   - **This is where your data will be stored**
   - Cost: Starts at ~$24/month for 400 RU/s

4. **Azure Key Vault** (Recommended)
   - Purpose: Securely store secrets (API keys, connection strings, etc.)
   - Why: Centralized secret management, rotation, audit logs

5. **Azure Front Door** OR **Application Gateway** (Optional)
   - Purpose: Load balancing, SSL termination, DDoS protection
   - Why: Production-grade traffic management

### Alternative: Simpler Architecture

If you want a simpler setup:
- **Azure App Service** (instead of Container Apps) - easier to configure
- **Azure Cosmos DB for MongoDB** - same database solution
- **Azure Container Registry** - for images

## Data Storage: MongoDB → Azure Cosmos DB

### Current Setup
- Local MongoDB running in Docker container
- Connection string: `mongodb://mongo:27017`
- Database name: `complytics`

### Azure Solution: Azure Cosmos DB for MongoDB API

**Why Cosmos DB?**
- 100% MongoDB API compatible (uses MongoDB drivers)
- Minimal code changes required
- Automatic backups, high availability
- Global distribution
- Auto-scaling

**Data Migration Path:**
1. Create Azure Cosmos DB account with MongoDB API
2. Get connection string from Azure Portal
3. Update environment variables
4. Migrate data using `mongodump` and `mongorestore` or Azure Data Migration tools

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Azure Front Door                      │
│              (Load Balancer / CDN)                       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐      ┌─────────▼──────────┐
│ Container App  │      │  Container App     │
│   (Frontend)   │      │    (Backend)       │
│   Nginx:80     │      │   FastAPI:8000     │
└────────────────┘      └─────────┬──────────┘
                                  │
                     ┌────────────▼────────────┐
                     │  Azure Cosmos DB        │
                     │  (MongoDB API)          │
                     │  Database: complytics   │
                     └─────────────────────────┘
```

## Step-by-Step Deployment Guide

### Prerequisites
- Azure account with active subscription
- Azure CLI installed (`az --version`)
- Docker installed locally
- Your application code

### Step 1: Create Azure Resources

#### 1.1 Login to Azure
```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

#### 1.2 Create Resource Group
```bash
az group create --name complytics-rg --location eastus
```

#### 1.3 Create Azure Container Registry
```bash
az acr create \
  --resource-group complytics-rg \
  --name complyticsregistry \
  --sku Basic \
  --admin-enabled true
```

#### 1.4 Create Azure Cosmos DB Account
```bash
az cosmosdb create \
  --name complytics-cosmos \
  --resource-group complytics-rg \
  --kind MongoDB \
  --locations regionName=eastus failoverPriority=0 \
  --default-consistency-level Session

# Create database
az cosmosdb mongodb database create \
  --account-name complytics-cosmos \
  --resource-group complytics-rg \
  --name complytics
```

#### 1.5 Get Cosmos DB Connection String
```bash
az cosmosdb keys list \
  --name complytics-cosmos \
  --resource-group complytics-rg \
  --type connection-strings
```

The connection string will look like:
```
mongodb://complytics-cosmos:YOUR_KEY@complytics-cosmos.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@complytics-cosmos@
```

#### 1.6 Create Azure Key Vault (Optional but Recommended)
```bash
az keyvault create \
  --name complytics-kv \
  --resource-group complytics-rg \
  --location eastus
```

### Step 2: Build and Push Docker Images

#### 2.1 Login to ACR
```bash
az acr login --name complyticsregistry
```

#### 2.2 Build and Push Backend Image
```bash
# Build
docker build -f Dockerfile.backend -t complyticsregistry.azurecr.io/complytics-backend:latest .

# Push
docker push complyticsregistry.azurecr.io/complytics-backend:latest
```

#### 2.3 Build and Push Frontend Image
```bash
# Build
docker build -f Dockerfile.frontend -t complyticsregistry.azurecr.io/complytics-frontend:latest .

# Push
docker push complyticsregistry.azurecr.io/complytics-frontend:latest
```

### Step 3: Create Container Apps Environment

#### 3.1 Create Container Apps Environment
```bash
az containerapp env create \
  --name complytics-env \
  --resource-group complytics-rg \
  --location eastus
```

#### 3.2 Create Backend Container App
```bash
az containerapp create \
  --name complytics-backend \
  --resource-group complytics-rg \
  --environment complytics-env \
  --image complyticsregistry.azurecr.io/complytics-backend:latest \
  --registry-server complyticsregistry.azurecr.io \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    MONGODB_URL="mongodb://complytics-cosmos:YOUR_KEY@complytics-cosmos.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@complytics-cosmos@" \
    MONGODB_NAME="complytics" \
    SECRET_KEY="your-secret-key" \
    ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES="30" \
    SMTP_HOST="smtp.gmail.com" \
    SMTP_PORT="587" \
    SMTP_USERNAME="your-email@gmail.com" \
    SMTP_PASSWORD="your-app-password" \
    SMTP_FROM_EMAIL="your-email@gmail.com"
```

#### 3.3 Create Frontend Container App
```bash
az containerapp create \
  --name complytics-frontend \
  --resource-group complytics-rg \
  --environment complytics-env \
  --image complyticsregistry.azurecr.io/complytics-frontend:latest \
  --registry-server complyticsregistry.azurecr.io \
  --target-port 80 \
  --ingress external
```

### Step 4: Update Frontend Configuration

You'll need to update your frontend to point to the backend URL. The backend URL will be something like:
`https://complytics-backend.xxxxx.azurecontainerapps.io`

Update your frontend API configuration to use this URL.

### Step 5: Migrate Data (Optional)

If you have existing data in local MongoDB:

```bash
# Export from local MongoDB
mongodump --uri="mongodb://localhost:27017" --db=complytics --out=./backup

# Import to Cosmos DB (use connection string from Step 1.5)
mongorestore --uri="YOUR_COSMOS_DB_CONNECTION_STRING" --db=complytics ./backup/complytics
```

## Alternative: Using Azure App Service (Simpler)

If Container Apps seems complex, use App Service:

### Create App Service Plan
```bash
az appservice plan create \
  --name complytics-plan \
  --resource-group complytics-rg \
  --sku B1 \
  --is-linux
```

### Create Backend Web App
```bash
az webapp create \
  --name complytics-backend \
  --resource-group complytics-rg \
  --plan complytics-plan \
  --deployment-container-image-name complyticsregistry.azurecr.io/complytics-backend:latest

# Configure container registry
az webapp config container set \
  --name complytics-backend \
  --resource-group complytics-rg \
  --docker-custom-image-name complyticsregistry.azurecr.io/complytics-backend:latest \
  --docker-registry-server-url https://complyticsregistry.azurecr.io \
  --docker-registry-server-user complyticsregistry \
  --docker-registry-server-password $(az acr credential show --name complyticsregistry --query "passwords[0].value" -o tsv)

# Set environment variables
az webapp config appsettings set \
  --resource-group complytics-rg \
  --name complytics-backend \
  --settings \
    MONGODB_URL="YOUR_COSMOS_DB_CONNECTION_STRING" \
    MONGODB_NAME="complytics" \
    SECRET_KEY="your-secret-key" \
    # ... other env vars
```

### Create Frontend Web App
```bash
az webapp create \
  --name complytics-frontend \
  --resource-group complytics-rg \
  --plan complytics-plan \
  --deployment-container-image-name complyticsregistry.azurecr.io/complytics-frontend:latest

# Configure similar to backend
```

## Environment Variables Configuration

### Required Environment Variables for Backend

Update these in Azure Portal or via CLI:

```bash
MONGODB_URL=<Cosmos DB connection string>
MONGODB_NAME=complytics
SECRET_KEY=<generate a secure random key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GOOGLE_API_KEY1=<your-google-api-key>
GOOGLE_API_KEY2=<your-google-api-key>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<your-email>
SMTP_PASSWORD=<your-app-password>
SMTP_FROM_EMAIL=<your-email>
```

### Using Azure Key Vault (Recommended for Production)

Store secrets in Key Vault and reference them:

```bash
# Store secrets
az keyvault secret set --vault-name complytics-kv --name mongodb-url --value "YOUR_CONNECTION_STRING"
az keyvault secret set --vault-name complytics-kv --name secret-key --value "YOUR_SECRET_KEY"

# Reference in Container App (requires Managed Identity setup)
# This requires additional configuration in Azure Portal
```

## Code Changes Required

### 1. Update CORS Origins (Backend)

Update `Complytics Backend/app.py` to include your Azure frontend URL:

```python
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://complytics-frontend.xxxxx.azurecontainerapps.io",  # Add this
    # ... other origins
]
```

### 2. Update API Base URL (Frontend)

Update your frontend API configuration to use the backend URL from Azure.

## Cost Estimation

### Monthly Costs (Approximate)

- **Azure Container Registry (Basic)**: ~$5/month
- **Azure Container Apps**: ~$0.000012/vCPU-second + $0.0000015/GB-second
  - Small app: ~$20-50/month
- **Azure Cosmos DB (400 RU/s)**: ~$24/month
- **Azure Key Vault**: ~$0.03/10K operations
- **Total**: ~$50-100/month for small-medium traffic

### Cost Optimization Tips

1. Use **Azure App Service** instead of Container Apps for simpler apps (cheaper)
2. Start with Cosmos DB **Autoscale** (scales down to 10% when not in use)
3. Use **Azure Dev/Test pricing** if eligible
4. Consider **Azure Database for MongoDB** (cheaper alternative, but less features)

## Monitoring and Logging

### Enable Application Insights
```bash
az monitor app-insights component create \
  --app complytics-insights \
  --location eastus \
  --resource-group complytics-rg

# Link to Container App
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --instrumentation-key <INSTRUMENTATION_KEY>
```

## Security Best Practices

1. **Use Managed Identity** for accessing Key Vault and Cosmos DB
2. **Enable HTTPS only** on all endpoints
3. **Use Azure Key Vault** for all secrets
4. **Enable firewall rules** on Cosmos DB (restrict to Container Apps IPs)
5. **Regular security updates** - enable auto-updates for container images
6. **Enable logging and monitoring** with Application Insights

## Troubleshooting

### Common Issues

1. **Connection to Cosmos DB fails**
   - Check firewall rules in Cosmos DB
   - Verify connection string format
   - Ensure SSL is enabled

2. **CORS errors**
   - Update CORS origins in backend
   - Check frontend URL matches exactly

3. **Container won't start**
   - Check logs: `az containerapp logs show --name complytics-backend --resource-group complytics-rg`
   - Verify environment variables are set correctly

## Next Steps

1. Set up CI/CD pipeline (Azure DevOps or GitHub Actions)
2. Configure custom domain names
3. Set up SSL certificates
4. Configure auto-scaling rules
5. Set up backup and disaster recovery
6. Configure monitoring alerts

## Additional Resources

- [Azure Container Apps Documentation](https://docs.microsoft.com/azure/container-apps/)
- [Azure Cosmos DB for MongoDB](https://docs.microsoft.com/azure/cosmos-db/mongodb/)
- [Azure Container Registry](https://docs.microsoft.com/azure/container-registry/)
- [Migrate MongoDB to Cosmos DB](https://docs.microsoft.com/azure/cosmos-db/mongodb/migrate)



