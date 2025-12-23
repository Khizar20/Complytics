#!/bin/bash

# Azure Deployment Script for Complytics
# This script automates the Azure deployment process

set -e  # Exit on error

# Configuration Variables
RESOURCE_GROUP="complytics-rg"
LOCATION="eastus"
ACR_NAME="complyticsregistry"
COSMOS_ACCOUNT="complytics-cosmos"
COSMOS_DB="complytics"
CONTAINER_ENV="complytics-env"
BACKEND_APP="complytics-backend"
FRONTEND_APP="complytics-frontend"
KEY_VAULT="complytics-kv"

echo "🚀 Starting Azure Deployment for Complytics..."

# Step 1: Login to Azure
echo "📋 Step 1: Checking Azure login..."
az account show > /dev/null 2>&1 || az login

# Step 2: Create Resource Group
echo "📋 Step 2: Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION || echo "Resource group already exists"

# Step 3: Create Azure Container Registry
echo "📋 Step 3: Creating Azure Container Registry..."
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true 2>/dev/null || echo "ACR already exists"

# Step 4: Create Cosmos DB
echo "📋 Step 4: Creating Azure Cosmos DB..."
az cosmosdb create \
  --name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --kind MongoDB \
  --locations regionName=$LOCATION failoverPriority=0 \
  --default-consistency-level Session 2>/dev/null || echo "Cosmos DB account already exists"

# Create database
az cosmosdb mongodb database create \
  --account-name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --name $COSMOS_DB 2>/dev/null || echo "Database already exists"

# Get connection string
echo "📋 Getting Cosmos DB connection string..."
CONNECTION_STRING=$(az cosmosdb keys list \
  --name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --type connection-strings \
  --query "connectionStrings[0].connectionString" -o tsv)

echo "✅ Cosmos DB Connection String:"
echo "$CONNECTION_STRING"
echo ""

# Step 5: Create Key Vault
echo "📋 Step 5: Creating Azure Key Vault..."
az keyvault create \
  --name $KEY_VAULT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION 2>/dev/null || echo "Key Vault already exists"

# Step 6: Build and Push Images
echo "📋 Step 6: Building and pushing Docker images..."

# Login to ACR
az acr login --name $ACR_NAME

# Build and push backend
echo "Building backend image..."
docker build -f Dockerfile.backend -t $ACR_NAME.azurecr.io/complytics-backend:latest .
docker push $ACR_NAME.azurecr.io/complytics-backend:latest

# Build and push frontend
echo "Building frontend image..."
docker build -f Dockerfile.frontend -t $ACR_NAME.azurecr.io/complytics-frontend:latest .
docker push $ACR_NAME.azurecr.io/complytics-frontend:latest

# Step 7: Create Container Apps Environment
echo "📋 Step 7: Creating Container Apps environment..."
az containerapp env create \
  --name $CONTAINER_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION 2>/dev/null || echo "Environment already exists"

# Step 8: Get ACR credentials
echo "📋 Step 8: Getting ACR credentials..."
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Step 9: Create Backend Container App
echo "📋 Step 9: Creating backend container app..."
az containerapp create \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_NAME.azurecr.io/complytics-backend:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars \
    MONGODB_URL="$CONNECTION_STRING" \
    MONGODB_NAME="$COSMOS_DB" \
    2>/dev/null || echo "Backend app already exists, updating..."

# Step 10: Create Frontend Container App
echo "📋 Step 10: Creating frontend container app..."
az containerapp create \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_NAME.azurecr.io/complytics-frontend:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 80 \
  --ingress external \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 2 \
  2>/dev/null || echo "Frontend app already exists, updating..."

# Get URLs
echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📌 Important URLs:"
BACKEND_URL=$(az containerapp show --name $BACKEND_APP --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)
FRONTEND_URL=$(az containerapp show --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Backend URL: https://$BACKEND_URL"
echo "Frontend URL: https://$FRONTEND_URL"
echo ""
echo "⚠️  Next Steps:"
echo "1. Update backend environment variables with your secrets:"
echo "   az containerapp update --name $BACKEND_APP --resource-group $RESOURCE_GROUP --set-env-vars SECRET_KEY='your-secret-key' ALGORITHM='HS256' ..."
echo ""
echo "2. Update frontend to use backend URL: $BACKEND_URL"
echo ""
echo "3. Update CORS in backend to allow: $FRONTEND_URL"
echo ""
echo "4. Migrate data from local MongoDB to Cosmos DB if needed"


































