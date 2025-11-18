# Azure Deployment Using Docker Hub

This guide shows how to deploy your Complytics app to Azure using Docker Hub images and Azure Cosmos DB.

## Architecture

```
Docker Hub (Public/Private Images)
    ↓
Azure Container Apps / Container Instances
    ↓
Azure Cosmos DB for MongoDB (Data Storage)
```

## Prerequisites

- Docker Hub account
- Azure account with active subscription
- Azure CLI installed

## Step 1: Push Images to Docker Hub

### 1.1 Login to Docker Hub
```bash
docker login
```

### 1.2 Build and Tag Images
```bash
# Build backend image
docker build -f Dockerfile.backend -t YOUR_DOCKERHUB_USERNAME/complytics-backend:latest .

# Build frontend image
docker build -f Dockerfile.frontend -t YOUR_DOCKERHUB_USERNAME/complytics-frontend:latest .
```

### 1.3 Push to Docker Hub
```bash
# Push backend
docker push YOUR_DOCKERHUB_USERNAME/complytics-backend:latest

# Push frontend
docker push YOUR_DOCKERHUB_USERNAME/complytics-frontend:latest
```

**Note**: Replace `YOUR_DOCKERHUB_USERNAME` with your actual Docker Hub username.

## Step 2: Create Azure Resources

### 2.1 Login to Azure
```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### 2.2 Create Resource Group
```bash
az group create --name complytics-rg --location eastus
```

### 2.3 Create Azure Cosmos DB
```bash
# Create Cosmos DB account
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

### 2.4 Get Cosmos DB Connection String
```bash
az cosmosdb keys list \
  --name complytics-cosmos \
  --resource-group complytics-rg \
  --type connection-strings \
  --query "connectionStrings[0].connectionString" -o tsv
```

**Save this connection string** - you'll need it for environment variables!

## Step 3: Deploy Using Azure Container Apps (Recommended)

### 3.1 Create Container Apps Environment
```bash
az containerapp env create \
  --name complytics-env \
  --resource-group complytics-rg \
  --location eastus
```

### 3.2 Deploy Backend Container
```bash
az containerapp create \
  --name complytics-backend \
  --resource-group complytics-rg \
  --environment complytics-env \
  --image YOUR_DOCKERHUB_USERNAME/complytics-backend:latest \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars \
    MONGODB_URL="YOUR_COSMOS_DB_CONNECTION_STRING" \
    MONGODB_NAME="complytics" \
    SECRET_KEY="your-secret-key-here" \
    ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES="30" \
    SMTP_HOST="smtp.gmail.com" \
    SMTP_PORT="587" \
    SMTP_USERNAME="your-email@gmail.com" \
    SMTP_PASSWORD="your-app-password" \
    SMTP_FROM_EMAIL="your-email@gmail.com"
```

**Important**: Replace:
- `YOUR_DOCKERHUB_USERNAME` with your Docker Hub username
- `YOUR_COSMOS_DB_CONNECTION_STRING` with the connection string from Step 2.4
- All other environment variables with your actual values

### 3.3 Deploy Frontend Container
```bash
az containerapp create \
  --name complytics-frontend \
  --resource-group complytics-rg \
  --environment complytics-env \
  --image YOUR_DOCKERHUB_USERNAME/complytics-frontend:latest \
  --target-port 80 \
  --ingress external \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 2
```

### 3.4 Get Your URLs
```bash
# Get backend URL
az containerapp show \
  --name complytics-backend \
  --resource-group complytics-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv

# Get frontend URL
az containerapp show \
  --name complytics-frontend \
  --resource-group complytics-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

## Step 4: Update Environment Variables (After Deployment)

### 4.1 Update Backend Environment Variables
```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --set-env-vars \
    MONGODB_URL="YOUR_COSMOS_DB_CONNECTION_STRING" \
    MONGODB_NAME="complytics" \
    SECRET_KEY="your-secret-key" \
    ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES="30" \
    GOOGLE_API_KEY1="your-google-api-key" \
    GOOGLE_API_KEY2="your-google-api-key" \
    SMTP_HOST="smtp.gmail.com" \
    SMTP_PORT="587" \
    SMTP_USERNAME="your-email@gmail.com" \
    SMTP_PASSWORD="your-app-password" \
    SMTP_FROM_EMAIL="your-email@gmail.com"
```

### 4.2 Using Azure Portal (Alternative)

1. Go to Azure Portal → Container Apps → `complytics-backend`
2. Click **Configuration** → **Environment variables**
3. Add/Edit each variable
4. Click **Save**

## Step 5: Update CORS in Backend

After getting your frontend URL, update CORS in your backend code:

**File**: `Complytics Backend/app.py`

```python
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://complytics-frontend.xxxxx.azurecontainerapps.io",  # Add your Azure frontend URL
]
```

Then rebuild and push to Docker Hub:
```bash
docker build -f Dockerfile.backend -t YOUR_DOCKERHUB_USERNAME/complytics-backend:latest .
docker push YOUR_DOCKERHUB_USERNAME/complytics-backend:latest
```

Update the container app to pull the new image:
```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --image YOUR_DOCKERHUB_USERNAME/complytics-backend:latest
```

## Alternative: Using Azure Container Instances (Simpler, but less features)

If you prefer a simpler option:

### Deploy Backend
```bash
az container create \
  --resource-group complytics-rg \
  --name complytics-backend \
  --image YOUR_DOCKERHUB_USERNAME/complytics-backend:latest \
  --dns-name-label complytics-backend \
  --ports 8000 \
  --environment-variables \
    MONGODB_URL="YOUR_COSMOS_DB_CONNECTION_STRING" \
    MONGODB_NAME="complytics" \
    SECRET_KEY="your-secret-key" \
    ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES="30" \
    SMTP_HOST="smtp.gmail.com" \
    SMTP_PORT="587" \
    SMTP_USERNAME="your-email@gmail.com" \
    SMTP_PASSWORD="your-password" \
    SMTP_FROM_EMAIL="your-email@gmail.com"
```

### Deploy Frontend
```bash
az container create \
  --resource-group complytics-rg \
  --name complytics-frontend \
  --image YOUR_DOCKERHUB_USERNAME/complytics-frontend:latest \
  --dns-name-label complytics-frontend \
  --ports 80
```

## Environment Variables Reference

### Required Variables for Backend:

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URL` | Cosmos DB connection string | `mongodb://account:key@account.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb` |
| `MONGODB_NAME` | Database name | `complytics` |
| `SECRET_KEY` | JWT secret key | Generate with: `openssl rand -hex 32` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `30` |
| `SMTP_HOST` | SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USERNAME` | Email username | `your-email@gmail.com` |
| `SMTP_PASSWORD` | Email app password | `your-app-password` |
| `SMTP_FROM_EMAIL` | From email | `your-email@gmail.com` |

### Optional Variables:

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY1` | Google API key |
| `GOOGLE_API_KEY2` | Google API key (backup) |

## Migrate Data from Local MongoDB to Cosmos DB

If you have existing data:

```bash
# Export from local MongoDB
mongodump --uri="mongodb://localhost:27017" --db=complytics --out=./backup

# Import to Cosmos DB (use connection string from Step 2.4)
mongorestore --uri="YOUR_COSMOS_DB_CONNECTION_STRING" --db=complytics ./backup/complytics
```

## Quick Commands Reference

### View Logs
```bash
# Container Apps
az containerapp logs show --name complytics-backend --resource-group complytics-rg --follow

# Container Instances
az container logs --name complytics-backend --resource-group complytics-rg --follow
```

### Update Environment Variables
```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --set-env-vars KEY="value"
```

### Restart Container
```bash
az containerapp revision restart \
  --name complytics-backend \
  --resource-group complytics-rg
```

### Delete Resources (Cleanup)
```bash
az group delete --name complytics-rg --yes --no-wait
```

## Cost Estimate

- **Container Apps**: ~$20-50/month (pay per use)
- **Cosmos DB**: ~$24/month (400 RU/s minimum)
- **Total**: ~$45-75/month

## Troubleshooting

### Container won't start
```bash
# Check logs
az containerapp logs show --name complytics-backend --resource-group complytics-rg
```

### Connection to Cosmos DB fails
- Verify connection string is correct
- Check Cosmos DB firewall settings (allow Azure services)
- Ensure SSL is enabled in connection string

### Images not pulling from Docker Hub
- Verify image name is correct
- Check if image is public or if you need to set up Docker Hub credentials in Azure

## Next Steps

1. ✅ Push images to Docker Hub
2. ✅ Create Cosmos DB
3. ✅ Deploy containers
4. ✅ Set environment variables
5. ✅ Update CORS
6. ✅ Migrate data
7. ✅ Test deployment


