#!/bin/bash

# Script to create Azure Service Principal for Jenkins CI/CD
# Run this script to create the service principal and get the credentials

echo "🔐 Creating Azure Service Principal for Jenkins..."
echo ""

# Set your subscription ID
SUBSCRIPTION_ID="e7057718-109b-4459-9a1e-8acfe7595e3b"
RESOURCE_GROUP="complytics-rg"
SP_NAME="jenkins-complytics-sp"

# Login to Azure (if not already logged in)
echo "📝 Logging in to Azure..."
az login

# Set subscription
echo "📝 Setting subscription..."
az account set --subscription "$SUBSCRIPTION_ID"

# Create service principal
echo "📝 Creating service principal..."
SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "$SP_NAME" \
  --role contributor \
  --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
  --output json)

# Extract values
CLIENT_ID=$(echo $SP_OUTPUT | jq -r '.appId')
CLIENT_SECRET=$(echo $SP_OUTPUT | jq -r '.password')
TENANT_ID=$(echo $SP_OUTPUT | jq -r '.tenant')

echo ""
echo "✅ Service Principal created successfully!"
echo ""
echo "📋 Use these credentials in Jenkins:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Client ID (Application ID):     $CLIENT_ID"
echo "Client Secret (Password):       $CLIENT_SECRET"
echo "Tenant ID:                      $TENANT_ID"
echo "Subscription ID:                $SUBSCRIPTION_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  IMPORTANT: Save the Client Secret now - you won't be able to see it again!"
echo ""
echo "📝 Next steps:"
echo "1. Go to Jenkins → Manage Jenkins → Manage Credentials"
echo "2. Add new credential with ID: azure-service-principal"
echo "3. Use the values above"
echo ""

