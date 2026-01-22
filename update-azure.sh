#!/bin/bash
set -e

# Configuration - Update these after first deployment
ACR_NAME=""
APP_NAME=""
RESOURCE_GROUP="d2d-rg"

# Check if variables are set
if [ -z "$ACR_NAME" ] || [ -z "$APP_NAME" ]; then
    echo "❌ Please edit update-azure.sh and set ACR_NAME and APP_NAME"
    echo ""
    echo "Find them with:"
    echo "  az containerapp list --resource-group $RESOURCE_GROUP -o table"
    echo "  az acr list --resource-group $RESOURCE_GROUP -o table"
    echo ""
    echo "Or check the output from your initial deployment (deploy-to-azure.sh)"
    exit 1
fi

echo "=== Updating D2D in Azure ==="
echo ""
echo "📦 Container Registry: $ACR_NAME"
echo "🚀 App Name: $APP_NAME"
echo "📁 Resource Group: $RESOURCE_GROUP"
echo ""

# Check if in correct directory
if [ ! -f "Dockerfile" ]; then
    echo "❌ Error: Dockerfile not found. Are you in /opt/d2d?"
    exit 1
fi

# Login to ACR
echo "Step 1: Logging in to Azure Container Registry..."
az acr login --name $ACR_NAME

# Build and push
echo "Step 2: Building and pushing new image..."
echo "This may take 2-3 minutes..."
az acr build --registry $ACR_NAME --image d2d:latest .

# Update container app
echo ""
echo "Step 3: Updating Container App..."
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/d2d:latest \
  --output none

echo ""
echo "✅ Update complete!"
echo ""

# Get URL
APP_URL=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "🌐 App URL: https://$APP_URL"
echo ""
echo "View logs:"
echo "  az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "Check status:"
echo "  az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.runningStatus"
echo ""
