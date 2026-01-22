# Deploy D2D to Azure

## Prerequisites
- Azure subscription
- Azure CLI installed: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`
- Docker installed locally
- VPN connection to your PACS network

## Option 1: Azure Container Instances (ACI) - Cheapest & Simplest

**Cost**: ~$15-30/month for always-on B1 instance
**Best for**: Simple deployment, predictable low usage

### Step 1: Login to Azure
```bash
az login
az account set --subscription "Your Subscription Name"
```

### Step 2: Create Resource Group
```bash
RESOURCE_GROUP="d2d-rg"
LOCATION="australiaeast"  # Or your preferred location

az group create --name $RESOURCE_GROUP --location $LOCATION
```

### Step 3: Create Azure Container Registry (ACR)
```bash
ACR_NAME="d2dacr$(date +%s)"  # Unique name

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --location $LOCATION
```

### Step 4: Build and Push Docker Image
```bash
cd /opt/d2d

# Login to ACR
az acr login --name $ACR_NAME

# Build and push
az acr build --registry $ACR_NAME --image d2d:latest .
```

### Step 5: Create Azure File Share for Persistent Storage
```bash
STORAGE_ACCOUNT="d2dstorage$(date +%s)"

az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS

# Create file share
az storage share create \
  --name d2darchive \
  --account-name $STORAGE_ACCOUNT

# Get storage key
STORAGE_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT \
  --query '[0].value' -o tsv)
```

### Step 6: Deploy Container to Existing VNet (if you have VPN)
```bash
# If you already have a VNet with VPN to on-prem:
az container create \
  --resource-group $RESOURCE_GROUP \
  --name d2d-container \
  --image $ACR_NAME.azurecr.io/d2d:latest \
  --registry-login-server $ACR_NAME.azurecr.io \
  --registry-username $(az acr credential show --name $ACR_NAME --query username -o tsv) \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
  --dns-name-label d2d-app-$(date +%s) \
  --ports 8000 \
  --cpu 0.5 \
  --memory 1 \
  --environment-variables \
    HOST=0.0.0.0 \
    PORT=8000 \
  --azure-file-volume-account-name $STORAGE_ACCOUNT \
  --azure-file-volume-account-key $STORAGE_KEY \
  --azure-file-volume-share-name d2darchive \
  --azure-file-volume-mount-path /app/dicom_archive \
  --subnet /subscriptions/YOUR_SUB_ID/resourceGroups/YOUR_RG/providers/Microsoft.Network/virtualNetworks/YOUR_VNET/subnets/YOUR_SUBNET

# Get the URL
az container show \
  --resource-group $RESOURCE_GROUP \
  --name d2d-container \
  --query ipAddress.fqdn -o tsv
```

---

## Option 2: Azure Container Apps - Serverless (Scales to Zero) ⭐ RECOMMENDED

**Cost**: ~$0-10/month (only pay when used, scales to zero)
**Best for**: Sporadic usage, auto-scaling needs

### Deploy with Container Apps
```bash
# Install containerapp extension
az extension add --name containerapp --upgrade

# Create Container Apps environment with your existing VNet
az containerapp env create \
  --name d2d-env \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --infrastructure-subnet-resource-id /subscriptions/YOUR_SUB/resourceGroups/YOUR_RG/providers/Microsoft.Network/virtualNetworks/YOUR_VNET/subnets/YOUR_SUBNET

# Create storage mount
az containerapp env storage set \
  --name d2d-env \
  --resource-group $RESOURCE_GROUP \
  --storage-name d2darchive \
  --azure-file-account-name $STORAGE_ACCOUNT \
  --azure-file-account-key $STORAGE_KEY \
  --azure-file-share-name d2darchive \
  --access-mode ReadWrite

# Deploy container app
az containerapp create \
  --name d2d-app \
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
  --env-vars \
    HOST=0.0.0.0 \
    PORT=8000

# Get the URL
az containerapp show \
  --name d2d-app \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv
```

---

## Quick Deploy Script (Recommended)

Save as `deploy-to-azure.sh`:

```bash
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
```

---

## Cost Comparison

| Option | Monthly Cost | Scales to Zero | Best For |
|--------|-------------|----------------|----------|
| **Container Apps** ⭐ | **$0-10** | **Yes** | **Sporadic usage, auto-scale** |
| Container Instances | $15-30 | No | Always-on, predictable load |
| App Service B1 | $55 | No | Managed features, built-in SSL |

---

## Connect to Your Existing VPN

If you already have an Azure VPN connection:

1. **Find your VNet details:**
```bash
az network vnet list --output table
az network vnet subnet list --resource-group YOUR_RG --vnet-name YOUR_VNET --output table
```

2. **Edit the deployment script:**
Set these variables:
```bash
USE_EXISTING_VNET="yes"
EXISTING_VNET_RG="your-vnet-resource-group"
EXISTING_VNET_NAME="your-vnet-name"
EXISTING_SUBNET_NAME="your-subnet-name"
```

3. **Deploy:**
```bash
./deploy-to-azure.sh
```

The container will be on your VPN-connected VNet and can reach your on-prem PACS servers!

---

## Testing DICOM Connectivity

After deployment, test connectivity to your PACS:

```bash
# SSH into a VM on the same VNet, or use Azure Cloud Shell
# Install DICOM toolkit
sudo apt install dcmtk

# Test C-ECHO to your PACS
echoscu -aet D2D_SCU -aec YOUR_PACS_AE YOUR_PACS_IP YOUR_PACS_PORT
```

If this works, your D2D app can send to PACS!

---

## Next Steps

1. **Install Azure CLI** (if not installed):
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

2. **Copy deployment script:**
```bash
sudo cp /home/claudeagent/d2d/deploy-to-azure.sh /opt/d2d/
sudo chown crowdit:crowdit /opt/d2d/deploy-to-azure.sh
chmod +x /opt/d2d/deploy-to-azure.sh
```

3. **Edit configuration** in the script (VNet details if using existing VPN)

4. **Run deployment:**
```bash
cd /opt/d2d
./deploy-to-azure.sh
```

5. **Access your app** at the provided HTTPS URL!

---

## Troubleshooting

**Container won't start:**
```bash
az containerapp logs show --name d2d-app-* --resource-group d2d-rg --follow
```

**Can't reach PACS:**
- Check VNet peering/VPN connection
- Verify DICOM ports (104, 11112) are allowed in NSG
- Test with echoscu from same VNet

**Update the app:**
```bash
cd /opt/d2d
az acr build --registry YOUR_ACR_NAME --image d2d:latest .
az containerapp update --name d2d-app-* --resource-group d2d-rg --image YOUR_ACR_NAME.azurecr.io/d2d:latest
```
