#!/bin/bash

# Quick Deployment Script for Azure using Docker Hub
# Usage: ./dockerhub-deploy.sh YOUR_DOCKERHUB_USERNAME

set -e

if [ -z "$1" ]; then
    echo "❌ Error: Docker Hub username required"
    echo "Usage: ./dockerhub-deploy.sh YOUR_DOCKERHUB_USERNAME"
    exit 1
fi

DOCKERHUB_USERNAME=$1
RESOURCE_GROUP="complytics-rg"
LOCATION="eastus"
COSMOS_ACCOUNT="complytics-cosmos"
COSMOS_DB="complytics"
CONTAINER_ENV="complytics-env"
BACKEND_APP="complytics-backend"
FRONTEND_APP="complytics-frontend"

echo "🚀 Starting Azure Deployment with Docker Hub..."
echo "📦 Docker Hub Username: $DOCKERHUB_USERNAME"
echo ""

# Step 1: Login to Azure
echo "📋 Step 1: Checking Azure login..."
az account show > /dev/null 2>&1 || az login

# Step 2: Create Resource Group
echo "📋 Step 2: Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION 2>/dev/null || echo "Resource group already exists"

# Step 3: Create Cosmos DB
echo "📋 Step 3: Creating Azure Cosmos DB..."
az cosmosdb create \
  --name $COSMOS_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --kind MongoDB \
  --locations regionName=$LOCATION failoverPriority=0 \
  --default-consistency-level Session 2>/dev/null || echo "Cosmos DB account already exists"

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

echo "✅ Cosmos DB Connection String retrieved"
echo ""

# Step 4: Create Container Apps Environment
echo "📋 Step 4: Creating Container Apps environment..."
az containerapp env create \
  --name $CONTAINER_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION 2>/dev/null || echo "Environment already exists"

# Step 5: Deploy Backend
echo "📋 Step 5: Deploying backend container..."
echo "⚠️  Note: You'll need to set environment variables manually after deployment"
az containerapp create \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $DOCKERHUB_USERNAME/complytics-backend:latest \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars \
    MONGODB_URL="$CONNECTION_STRING" \
    MONGODB_NAME="$COSMOS_DB" \
    2>/dev/null || echo "Backend app already exists"

# Step 6: Deploy Frontend
echo "📋 Step 6: Deploying frontend container..."
az containerapp create \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $DOCKERHUB_USERNAME/complytics-frontend:latest \
  --target-port 80 \
  --ingress external \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 2 \
  2>/dev/null || echo "Frontend app already exists"

# Get URLs
echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📌 Important Information:"
echo ""
BACKEND_URL=$(az containerapp show --name $BACKEND_APP --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)
FRONTEND_URL=$(az containerapp show --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Backend URL: https://$BACKEND_URL"
echo "Frontend URL: https://$FRONTEND_URL"
echo ""
echo "Cosmos DB Connection String:"
echo "$CONNECTION_STRING"
echo ""
echo "⚠️  Next Steps:"
echo ""
echo "1. Set remaining environment variables:"
echo "   az containerapp update --name $BACKEND_APP --resource-group $RESOURCE_GROUP --set-env-vars \\"
echo "     SECRET_KEY='your-secret-key' \\"
echo "     ALGORITHM='HS256' \\"
echo "     ACCESS_TOKEN_EXPIRE_MINUTES='30' \\"
echo "     SMTP_HOST='smtp.gmail.com' \\"
echo "     SMTP_PORT='587' \\"
echo "     SMTP_USERNAME='your-email@gmail.com' \\"
echo "     SMTP_PASSWORD='your-password' \\"
echo "     SMTP_FROM_EMAIL='your-email@gmail.com'"
echo ""
echo "2. Update CORS in backend to allow: $FRONTEND_URL"
echo ""
echo "3. Rebuild and push backend image with updated CORS"
echo ""
echo "4. Update container app:"
echo "   az containerapp update --name $BACKEND_APP --resource-group $RESOURCE_GROUP --image $DOCKERHUB_USERNAME/complytics-backend:latest"


















