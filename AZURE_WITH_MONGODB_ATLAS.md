# Azure Deployment Using Docker Hub + MongoDB Atlas

This guide shows how to deploy your Complytics app to Azure using Docker Hub images and MongoDB Atlas (instead of Azure Cosmos DB).

## Architecture

```
Docker Hub (Public/Private Images)
    ↓
Azure Container Apps / Container Instances
    ↓
MongoDB Atlas (Cloud MongoDB - Data Storage)
```

## Why MongoDB Atlas?

✅ **Easier migration** - Same MongoDB, no changes needed  
✅ **Free tier available** - M0 cluster (512MB storage)  
✅ **Familiar interface** - Same MongoDB you're using now  
✅ **Better MongoDB features** - Full MongoDB compatibility  
✅ **Simpler setup** - Just get connection string and use it  

## Prerequisites

- Docker Hub account
- MongoDB Atlas account (free at https://www.mongodb.com/cloud/atlas)
- Azure account with active subscription
- Azure CLI installed

---

## Step 1: Set Up MongoDB Atlas

### 1.1 Create MongoDB Atlas Account
1. Go to https://www.mongodb.com/cloud/atlas
2. Sign up for free account
3. Create a new project (e.g., "Complytics")

### 1.2 Create a Free Cluster
1. Click **"Build a Database"**
2. Choose **FREE (M0)** tier
3. Select cloud provider and region (choose closest to your Azure region)
4. Name your cluster (e.g., "complytics-cluster")
5. Click **"Create"**

### 1.3 Configure Database Access
1. Go to **Database Access** → **Add New Database User**
2. Choose **Password** authentication
3. Create username and password (SAVE THESE!)
4. Set privileges to **"Atlas admin"** or **"Read and write to any database"**
5. Click **"Add User"**

### 1.4 Configure Network Access
1. Go to **Network Access** → **Add IP Address**
2. For Azure Container Apps, click **"Allow Access from Anywhere"** (0.0.0.0/0)
   - Or add specific Azure IP ranges for better security
3. Click **"Confirm"**

### 1.5 Get Connection String
1. Go to **Database** → Click **"Connect"** on your cluster
2. Choose **"Connect your application"**
3. Select **Driver**: Python, **Version**: 3.6 or later
4. Copy the connection string

It will look like:
```
mongodb+srv://<username>:<password>@complytics-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

**Replace `<username>` and `<password>` with your actual credentials:**
```
mongodb+srv://myuser:mypassword@complytics-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

### 1.6 Create Database
1. Click **"Browse Collections"**
2. Click **"Add My Own Data"**
3. Database name: `complytics`
4. Collection name: (any name, e.g., `users`)

**Or** - The database will be created automatically when your app connects!

---

## Step 2: Push Images to Docker Hub

### 2.1 Login to Docker Hub
```bash
docker login
```

### 2.2 Build and Tag Images
```bash
# Build backend image
docker build -f Dockerfile.backend -t YOUR_DOCKERHUB_USERNAME/complytics-backend:latest .

# Build frontend image
docker build -f Dockerfile.frontend -t YOUR_DOCKERHUB_USERNAME/complytics-frontend:latest .
```

### 2.3 Push to Docker Hub
```bash
# Push backend
docker push YOUR_DOCKERHUB_USERNAME/complytics-backend:latest

# Push frontend
docker push YOUR_DOCKERHUB_USERNAME/complytics-frontend:latest
```

**Note**: Replace `YOUR_DOCKERHUB_USERNAME` with your actual Docker Hub username.

---

## Step 3: Create Azure Resources

### 3.1 Login to Azure
```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### 3.2 Create Resource Group
```bash
az group create --name complytics-rg --location eastus
```

**No need to create Cosmos DB!** We're using MongoDB Atlas instead.

---

## Step 4: Deploy Using Azure Container Apps

### 4.1 Create Container Apps Environment
```bash
az containerapp env create \
  --name complytics-env \
  --resource-group complytics-rg \
  --location eastus
```

### 4.2 Deploy Backend Container
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
    MONGODB_URL="mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority" \
    MONGODB_NAME="complytics"
```

**Important**: 
- Replace `YOUR_DOCKERHUB_USERNAME` with your Docker Hub username
- Replace the `MONGODB_URL` with your MongoDB Atlas connection string from Step 1.5
- Make sure to URL-encode the password if it contains special characters

### 4.3 Deploy Frontend Container
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

### 4.4 Get Your URLs
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

---

## Step 5: Set Environment Variables

### 5.1 Update Backend Environment Variables
```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --set-env-vars \
    MONGODB_URL="mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority" \
    MONGODB_NAME="complytics" \
    SECRET_KEY="your-secret-key-here" \
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

### 5.2 Using Azure Portal (Alternative)

1. Go to Azure Portal → Container Apps → `complytics-backend`
2. Click **Configuration** → **Environment variables**
3. Add/Edit each variable:
   - `MONGODB_URL`: Your MongoDB Atlas connection string
   - `MONGODB_NAME`: `complytics`
   - `SECRET_KEY`: Generate with `openssl rand -hex 32`
   - All other variables as needed
4. Click **Save**

---

## Step 6: Update CORS in Backend

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

Update the container app:
```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --image YOUR_DOCKERHUB_USERNAME/complytics-backend:latest
```

---

## Step 7: Migrate Data (If You Have Existing Data)

### Option 1: Using mongodump/mongorestore
```bash
# Export from local MongoDB
mongodump --uri="mongodb://localhost:27017" --db=complytics --out=./backup

# Import to MongoDB Atlas (use connection string from Step 1.5)
mongorestore --uri="mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority" --db=complytics ./backup/complytics
```

### Option 2: Using MongoDB Compass (GUI)
1. Download MongoDB Compass: https://www.mongodb.com/products/compass
2. Connect to local MongoDB
3. Export collections
4. Connect to MongoDB Atlas
5. Import collections

### Option 3: Using MongoDB Atlas Data Import
1. Go to MongoDB Atlas → Your Cluster → **"..."** → **"Load Sample Dataset"** or **"Import Data"**
2. Follow the import wizard

---

## Environment Variables Reference

### Required Variables for Backend:

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority` |
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

---

## MongoDB Atlas Connection String Format

### Standard Format:
```
mongodb+srv://<username>:<password>@<cluster-name>.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

### With Database Name:
```
mongodb+srv://<username>:<password>@<cluster-name>.xxxxx.mongodb.net/complytics?retryWrites=true&w=majority
```

### URL Encoding Special Characters:
If your password contains special characters, URL-encode them:
- `@` → `%40`
- `:` → `%3A`
- `/` → `%2F`
- `?` → `%3F`
- `#` → `%23`
- `[` → `%5B`
- `]` → `%5D`

Example:
```
Password: p@ssw:rd
Encoded: p%40ssw%3Ard
Connection string: mongodb+srv://user:p%40ssw%3Ard@cluster.xxxxx.mongodb.net/...
```

---

## Quick Commands Reference

### View Logs
```bash
az containerapp logs show --name complytics-backend --resource-group complytics-rg --follow
```

### Update Environment Variables
```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --set-env-vars MONGODB_URL="new-connection-string"
```

### Restart Container
```bash
az containerapp revision restart \
  --name complytics-backend \
  --resource-group complytics-rg
```

### Test MongoDB Atlas Connection
```bash
# From your local machine (install mongosh if needed)
mongosh "mongodb+srv://username:password@cluster.xxxxx.mongodb.net/complytics"
```

---

## Cost Comparison

### MongoDB Atlas:
- **Free Tier (M0)**: 512MB storage, shared CPU/RAM - **FREE**
- **M10**: 10GB storage, 2GB RAM - ~$57/month
- **M20**: 20GB storage, 4GB RAM - ~$120/month

### Azure Cosmos DB:
- **400 RU/s**: ~$24/month minimum
- Scales up from there

**For development/testing**: MongoDB Atlas free tier is perfect!  
**For production**: Choose based on your needs.

---

## Troubleshooting

### Connection to MongoDB Atlas fails

1. **Check Network Access**
   - Go to MongoDB Atlas → Network Access
   - Ensure Azure IPs are allowed (or use 0.0.0.0/0 for testing)

2. **Verify Connection String**
   - Make sure username and password are correct
   - URL-encode special characters in password
   - Check cluster name is correct

3. **Check Database User Permissions**
   - Go to Database Access
   - Ensure user has read/write permissions

4. **Test Connection Locally**
   ```bash
   mongosh "your-connection-string"
   ```

### Container won't start
```bash
# Check logs
az containerapp logs show --name complytics-backend --resource-group complytics-rg
```

### "Authentication failed" error
- Double-check username and password in connection string
- Ensure user exists in MongoDB Atlas
- Check user has proper permissions

---

## Security Best Practices

1. **Don't hardcode credentials** - Use environment variables
2. **Use IP whitelisting** - Restrict network access to Azure IPs only
3. **Use strong passwords** - For database users
4. **Enable encryption** - MongoDB Atlas encrypts data at rest by default
5. **Regular backups** - MongoDB Atlas provides automated backups (paid tiers)
6. **Monitor access** - Check MongoDB Atlas logs regularly

---

## Next Steps

1. ✅ Create MongoDB Atlas account and cluster
2. ✅ Get connection string
3. ✅ Push images to Docker Hub
4. ✅ Deploy containers to Azure
5. ✅ Set environment variables
6. ✅ Update CORS
7. ✅ Migrate data (if needed)
8. ✅ Test deployment

---

## Summary

**Yes, you can absolutely use MongoDB Atlas instead of Azure Cosmos DB!**

**Advantages:**
- ✅ Free tier available
- ✅ Same MongoDB you're already using
- ✅ No code changes needed
- ✅ Easier migration
- ✅ Better MongoDB feature support

**Just update the `MONGODB_URL` environment variable with your MongoDB Atlas connection string!**







