# Simple Azure Deployment - Step by Step

## What You'll Do:
1. Push images to Docker Hub ✅
2. Create Azure Cosmos DB (replaces MongoDB) ✅
3. Deploy containers from Docker Hub ✅
4. Set environment variables ✅

---

## Step 1: Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Build and push backend
docker build -f Dockerfile.backend -t YOUR_USERNAME/complytics-backend:latest .
docker push YOUR_USERNAME/complytics-backend:latest

# Build and push frontend
docker build -f Dockerfile.frontend -t YOUR_USERNAME/complytics-frontend:latest .
docker push YOUR_USERNAME/complytics-frontend:latest
```

---

## Step 2: Create Azure Cosmos DB

```bash
# Login to Azure
az login

# Create resource group
az group create --name complytics-rg --location eastus

# Create Cosmos DB
az cosmosdb create \
  --name complytics-cosmos \
  --resource-group complytics-rg \
  --kind MongoDB \
  --locations regionName=eastus failoverPriority=0

# Create database
az cosmosdb mongodb database create \
  --account-name complytics-cosmos \
  --resource-group complytics-rg \
  --name complytics

# Get connection string (SAVE THIS!)
az cosmosdb keys list \
  --name complytics-cosmos \
  --resource-group complytics-rg \
  --type connection-strings \
  --query "connectionStrings[0].connectionString" -o tsv
```

**Copy the connection string** - you'll need it!

---

## Step 3: Deploy Containers

```bash
# Create Container Apps environment
az containerapp env create \
  --name complytics-env \
  --resource-group complytics-rg \
  --location eastus

# Deploy backend (replace YOUR_USERNAME and CONNECTION_STRING)
az containerapp create \
  --name complytics-backend \
  --resource-group complytics-rg \
  --environment complytics-env \
  --image YOUR_USERNAME/complytics-backend:latest \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2.0Gi \
  --env-vars \
    MONGODB_URL="CONNECTION_STRING_FROM_STEP_2" \
    MONGODB_NAME="complytics"

# Deploy frontend
az containerapp create \
  --name complytics-frontend \
  --resource-group complytics-rg \
  --environment complytics-env \
  --image YOUR_USERNAME/complytics-frontend:latest \
  --target-port 80 \
  --ingress external \
  --cpu 0.5 \
  --memory 1.0Gi
```

---

## Step 4: Set Environment Variables

```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --set-env-vars \
    MONGODB_URL="YOUR_COSMOS_DB_CONNECTION_STRING" \
    MONGODB_NAME="complytics" \
    SECRET_KEY="generate-with-openssl-rand-hex-32" \
    ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES="30" \
    SMTP_HOST="smtp.gmail.com" \
    SMTP_PORT="587" \
    SMTP_USERNAME="your-email@gmail.com" \
    SMTP_PASSWORD="your-app-password" \
    SMTP_FROM_EMAIL="your-email@gmail.com" \
    GOOGLE_API_KEY1="your-key" \
    GOOGLE_API_KEY2="your-key"
```

**Or use Azure Portal:**
1. Go to Azure Portal
2. Container Apps → complytics-backend
3. Configuration → Environment variables
4. Add each variable
5. Save

---

## Step 5: Get Your URLs

```bash
# Backend URL
az containerapp show \
  --name complytics-backend \
  --resource-group complytics-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv

# Frontend URL
az containerapp show \
  --name complytics-frontend \
  --resource-group complytics-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

---

## Step 6: Update CORS (Important!)

After getting your frontend URL, update `Complytics Backend/app.py`:

```python
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://complytics-frontend.xxxxx.azurecontainerapps.io",  # Add your frontend URL
]
```

Then rebuild and push:
```bash
docker build -f Dockerfile.backend -t YOUR_USERNAME/complytics-backend:latest .
docker push YOUR_USERNAME/complytics-backend:latest
az containerapp update --name complytics-backend --resource-group complytics-rg --image YOUR_USERNAME/complytics-backend:latest
```

---

## That's It! ✅

Your app is now deployed:
- **Data stored in**: Azure Cosmos DB for MongoDB
- **Containers running**: Azure Container Apps
- **Images from**: Docker Hub

---

## Quick Reference

### View Logs
```bash
az containerapp logs show --name complytics-backend --resource-group complytics-rg --follow
```

### Update Environment Variable
```bash
az containerapp update --name complytics-backend --resource-group complytics-rg --set-env-vars KEY="value"
```

### Restart Container
```bash
az containerapp revision restart --name complytics-backend --resource-group complytics-rg
```

---

## Cost: ~$50-75/month

- Container Apps: ~$20-50/month
- Cosmos DB: ~$24/month







