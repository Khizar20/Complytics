# Azure Environment Variables Setup

This document lists all environment variables needed for Azure deployment.

## Backend Environment Variables

Set these in Azure Container Apps or App Service:

### Database Configuration
```bash
MONGODB_URL=<Azure Cosmos DB connection string>
MONGODB_NAME=complytics
```

### Authentication
```bash
SECRET_KEY=<generate a secure random key, e.g., openssl rand -hex 32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Google API Keys (Optional)
```bash
GOOGLE_API_KEY1=<your-google-api-key>
GOOGLE_API_KEY2=<your-google-api-key>
```

### SMTP Configuration
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<your-email@gmail.com>
SMTP_PASSWORD=<your-app-specific-password>
SMTP_FROM_EMAIL=<your-email@gmail.com>
```

## Setting Environment Variables

### Using Azure CLI (Container Apps)

```bash
az containerapp update \
  --name complytics-backend \
  --resource-group complytics-rg \
  --set-env-vars \
    MONGODB_URL="your-connection-string" \
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

### Using Azure CLI (App Service)

```bash
az webapp config appsettings set \
  --resource-group complytics-rg \
  --name complytics-backend \
  --settings \
    MONGODB_URL="your-connection-string" \
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

### Using Azure Portal

1. Navigate to your Container App or App Service
2. Go to **Configuration** → **Environment variables**
3. Add each variable
4. Click **Save**

## Using Azure Key Vault (Recommended for Production)

For sensitive values, store them in Key Vault:

```bash
# Store secrets
az keyvault secret set --vault-name complytics-kv --name mongodb-url --value "your-connection-string"
az keyvault secret set --vault-name complytics-kv --name secret-key --value "your-secret-key"
az keyvault secret set --vault-name complytics-kv --name smtp-password --value "your-smtp-password"

# Reference in Container App (requires Managed Identity)
# This needs to be configured in Azure Portal under Identity settings
```

## Generating Secure Keys

### Generate SECRET_KEY
```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

## Getting Cosmos DB Connection String

```bash
az cosmosdb keys list \
  --name complytics-cosmos \
  --resource-group complytics-rg \
  --type connection-strings \
  --query "connectionStrings[0].connectionString" -o tsv
```

Or from Azure Portal:
1. Navigate to your Cosmos DB account
2. Go to **Connection String** under **Settings**
3. Copy the **Primary Connection String**

## Frontend Environment Variables

If your frontend needs environment variables at build time, you can set them:

```bash
# For Container Apps
az containerapp update \
  --name complytics-frontend \
  --resource-group complytics-rg \
  --set-env-vars \
    REACT_APP_API_URL="https://complytics-backend.xxxxx.azurecontainerapps.io"
```

Note: For React apps, environment variables must start with `REACT_APP_` to be accessible in the browser.







