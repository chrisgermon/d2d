#!/bin/bash
set -e

# ===== CONFIGURATION =====
RESOURCE_GROUP="d2d-rg"
LOCATION="australiaeast"  # Change to your region
USE_EXISTING_VNET="no"    # Set to "yes" if you have VPN already

# If using existing VNet, fill these in:
EXISTING_VNET_RG=""
EXISTING_VNET_NAME=""
EXISTING_SUBNET_NAME=""

# ===== END CONFIGURATION =====

echo "=== D2D Azure Deployment ==="
echo ""

# Unique names
ACR_NAME="d2dacr$(date +%s | tail -c 8)"
STORAGE_ACCOUNT="d2dstor$(date +%s | tail -c 8)"
APP_NAME="d2d-app-$(date +%s | tail -c 6)"

# Login
echo "Step 1: Logging in to Azure..."
az login

# Create resource group
echo "Step 2: Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION --output none

# Create ACR
echo "Step 3: Creating container registry..."
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --output none

# Build and push image
echo "Step 4: Building and pushing Docker image..."
cd /opt/d2d
az acr login --name $ACR_NAME
az acr build --registry $ACR_NAME --image d2d:latest . --output none

# Create storage
echo "Step 5: Creating storage account..."
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --sku Standard_LRS \
  --output none

az storage share create \
  --name d2darchive \
  --account-name $STORAGE_ACCOUNT \
  --output none

STORAGE_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT \
  --query '[0].value' -o tsv)

# Install Container Apps extension
echo "Step 6: Setting up Container Apps..."
az extension add --name containerapp --upgrade --output none 2>/dev/null || true

# Create Container Apps environment
if [ "$USE_EXISTING_VNET" = "yes" ]; then
    SUBNET_ID="/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$EXISTING_VNET_RG/providers/Microsoft.Network/virtualNetworks/$EXISTING_VNET_NAME/subnets/$EXISTING_SUBNET_NAME"

    az containerapp env create \
      --name d2d-env \
      --resource-group $RESOURCE_GROUP \
      --location $LOCATION \
      --infrastructure-subnet-resource-id $SUBNET_ID \
      --output none
else
    az containerapp env create \
      --name d2d-env \
      --resource-group $RESOURCE_GROUP \
      --location $LOCATION \
      --output none
fi

# Configure storage
az containerapp env storage set \
  --name d2d-env \
  --resource-group $RESOURCE_GROUP \
  --storage-name d2darchive \
  --azure-file-account-name $STORAGE_ACCOUNT \
  --azure-file-account-key $STORAGE_KEY \
  --azure-file-share-name d2darchive \
  --access-mode ReadWrite \
  --output none

# Deploy app
echo "Step 7: Deploying container app..."
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment d2d-env \
  --image $ACR_NAME.azurecr.io/d2d:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $(az acr credential show --name $ACR_NAME --query username -o tsv) \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
  --target-port 8000 \
  --ingress external \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 0 \
  --max-replicas 2 \
  --env-vars HOST=0.0.0.0 PORT=8000 \
  --output none

# Get URL
APP_URL=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "=== ✅ Deployment Complete! ==="
echo ""
echo "🌐 Application URL: https://$APP_URL"
echo "📦 Container Registry: $ACR_NAME"
echo "💾 Storage Account: $STORAGE_ACCOUNT"
echo "📁 Resource Group: $RESOURCE_GROUP"
echo ""
echo "To update the app:"
echo "  cd /opt/d2d"
echo "  az acr build --registry $ACR_NAME --image d2d:latest ."
echo "  az containerapp update --name $APP_NAME --resource-group $RESOURCE_GROUP --image $ACR_NAME.azurecr.io/d2d:latest"
echo ""
echo "To view logs:"
echo "  az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "To delete everything:"
echo "  az group delete --name $RESOURCE_GROUP --yes"
echo ""
