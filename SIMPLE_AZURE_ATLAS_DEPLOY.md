# Simple Azure + MongoDB Atlas Deployment

## Quick Steps:

1. **MongoDB Atlas** (Free tier available) ✅
2. **Docker Hub** (Push images) ✅
3. **Azure Container Apps** (Deploy containers) ✅
4. **Set environment variables** ✅

---

## Step 1: MongoDB Atlas Setup (5 minutes)

1. Go to https://www.mongodb.com/cloud/atlas → Sign up (FREE)
2. Create cluster → Choose **FREE (M0)**
3. **Database Access** → Create user (username + password)
4. **Network Access** → Allow from anywhere (0.0.0.0/0) or add Azure IPs
5. **Connect** → Choose "Connect your application" → Copy connection string

**Connection string looks like:**
```
mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

**Replace `<username>` and `<password>` with your actual credentials!**

---

## Step 2: Push to Docker Hub

```bash
docker login
docker build -f Dockerfile.backend -t YOUR_USERNAME/complytics-backend:latest .
docker push YOUR_USERNAME/complytics-backend:latest

docker build -f Dockerfile.frontend -t YOUR_USERNAME/complytics-frontend:latest .
docker push YOUR_USERNAME/complytics-frontend:latest
```

---

## Step 3: Deploy to Azure

```bash
# Login to Azure
az login

# Create resource group
az group create --name complytics-rg --location eastus

# Create Container Apps environment
az containerapp env create \
  --name complytics-env \
  --resource-group complytics-rg \
  --location eastus

# Deploy backend
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
    MONGODB_URL="mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority" \
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

## Step 4: Set All Environment Variables

```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --set-env-vars \
    MONGODB_URL="mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority" \
    MONGODB_NAME="complytics" \
    SECRET_KEY="generate-with-openssl-rand-hex-32" \
    ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES="30" \
    SMTP_HOST="smtp.gmail.com" \
    SMTP_PORT="587" \
    SMTP_USERNAME="your-email@gmail.com" \
    SMTP_PASSWORD="your-app-password" \
    SMTP_FROM_EMAIL="your-email@gmail.com"
```

**Or use Azure Portal:**
- Container Apps → complytics-backend → Configuration → Environment variables

---

## Step 5: Get URLs

```bash
# Backend
az containerapp show --name complytics-backend --resource-group complytics-rg --query "properties.configuration.ingress.fqdn" -o tsv

# Frontend
az containerapp show --name complytics-frontend --resource-group complytics-rg --query "properties.configuration.ingress.fqdn" -o tsv
```

---

## Step 6: Update CORS

Update `Complytics Backend/app.py`:
```python
origins = [
    "http://localhost:5173",
    "https://complytics-frontend.xxxxx.azurecontainerapps.io",  # Your frontend URL
]
```

Rebuild and push:
```bash
docker build -f Dockerfile.backend -t YOUR_USERNAME/complytics-backend:latest .
docker push YOUR_USERNAME/complytics-backend:latest
az containerapp update --name complytics-backend --resource-group complytics-rg --image YOUR_USERNAME/complytics-backend:latest
```

---

## Migrate Data (If Needed)

```bash
# Export from local
mongodump --uri="mongodb://localhost:27017" --db=complytics --out=./backup

# Import to Atlas
mongorestore --uri="mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority" --db=complytics ./backup/complytics
```

---

## Cost

- **MongoDB Atlas**: FREE (M0 tier) or ~$57/month (M10)
- **Azure Container Apps**: ~$20-50/month
- **Total**: ~$20-50/month (with free Atlas) or ~$77-107/month (with M10)

---

## That's It! ✅

- **Data stored in**: MongoDB Atlas (cloud MongoDB)
- **Containers**: Azure Container Apps
- **Images**: Docker Hub

**Much simpler than Cosmos DB - same MongoDB you're already using!**


