# PowerShell script to create Azure Service Principal for Jenkins CI/CD
# Run this script in PowerShell to create the service principal and get the credentials

Write-Host "🔐 Creating Azure Service Principal for Jenkins..." -ForegroundColor Cyan
Write-Host ""

# Set your subscription ID
$SUBSCRIPTION_ID = "e7057718-109b-4459-9a1e-8acfe7595e3b"
$RESOURCE_GROUP = "complytics-rg"
$SP_NAME = "jenkins-complytics-sp"

# Login to Azure (if not already logged in)
Write-Host "📝 Logging in to Azure..." -ForegroundColor Yellow
az login

# Set subscription
Write-Host "📝 Setting subscription..." -ForegroundColor Yellow
az account set --subscription $SUBSCRIPTION_ID

# Create service principal
Write-Host "📝 Creating service principal..." -ForegroundColor Yellow
$SP_OUTPUT = az ad sp create-for-rbac `
  --name $SP_NAME `
  --role contributor `
  --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" `
  --output json | ConvertFrom-Json

# Extract values
$CLIENT_ID = $SP_OUTPUT.appId
$CLIENT_SECRET = $SP_OUTPUT.password
$TENANT_ID = $SP_OUTPUT.tenant

Write-Host ""
Write-Host "✅ Service Principal created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Use these credentials in Jenkins:" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "Client ID (Application ID):     $CLIENT_ID" -ForegroundColor White
Write-Host "Client Secret (Password):       $CLIENT_SECRET" -ForegroundColor White
Write-Host "Tenant ID:                      $TENANT_ID" -ForegroundColor White
Write-Host "Subscription ID:                $SUBSCRIPTION_ID" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  IMPORTANT: Save the Client Secret now - you won't be able to see it again!" -ForegroundColor Red
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "1. Go to Jenkins → Manage Jenkins → Manage Credentials"
Write-Host "2. Add new credential with ID: azure-service-principal"
Write-Host "3. Use the values above"
Write-Host ""

