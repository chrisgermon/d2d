# Azure Deployment Setup for D2D

Since you already have Azure connectivity, here's how to deploy D2D:

## Step 1: Install Azure CLI (one-time)

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

## Step 2: Discover Your VNet Configuration

```bash
cd /opt/d2d
./find-azure-vnet.sh
```

This will:
- Show all your VNets
- Detect VPN/ExpressRoute connections
- List available subnets
- Generate configuration for deployment

## Step 3: Edit Deployment Script

Copy the configuration from Step 2 into `deploy-to-azure.sh`:

```bash
nano /opt/d2d/deploy-to-azure.sh
```

Update these lines:
```bash
USE_EXISTING_VNET="yes"
EXISTING_VNET_RG="your-resource-group"
EXISTING_VNET_NAME="your-vnet-name"
EXISTING_SUBNET_NAME="your-subnet-name"
LOCATION="australiaeast"  # or your location
```

## Step 4: Deploy to Azure

```bash
cd /opt/d2d
./deploy-to-azure.sh
```

The script will:
1. Create Azure Container Registry
2. Build and push Docker image
3. Create storage for archives
4. Deploy to Azure Container Apps (serverless)
5. Connect to your existing VPN/VNet

## Step 5: Access Your App

You'll get an HTTPS URL like:
```
https://d2d-app-xxxxx.australiaeast.azurecontainerapps.io
```

## Step 6: Test DICOM Connectivity

From Azure Cloud Shell or a VM in the same VNet:

```bash
# Install DICOM toolkit
sudo apt install dcmtk

# Test connection to your PACS
echoscu -aet D2D_SCU -aec YOUR_PACS_AE YOUR_PACS_IP YOUR_PACS_PORT
```

If this works, your D2D app will be able to send DICOM files to your PACS!

---

## Quick Command Summary

```bash
# 1. Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 2. Find VNet
cd /opt/d2d
./find-azure-vnet.sh

# 3. Edit config (paste values from step 2)
nano deploy-to-azure.sh

# 4. Deploy
./deploy-to-azure.sh

# 5. Access the URL provided
```

---

## Estimated Costs

**Azure Container Apps (Recommended)**
- **Monthly**: $0-10 (scales to zero when not in use)
- **Per conversion**: ~$0.001
- Storage: ~$0.50/month for 10GB

**Total for light usage**: ~$1-5/month

---

## Update the App Later

```bash
cd /opt/d2d
az acr build --registry YOUR_ACR_NAME --image d2d:latest .
az containerapp update --name YOUR_APP_NAME --resource-group d2d-rg --image YOUR_ACR_NAME.azurecr.io/d2d:latest
```

---

## Troubleshooting

**Can't reach PACS from Azure:**
1. Check VPN/ExpressRoute is active
2. Verify Network Security Group allows DICOM ports
3. Test with echoscu from same VNet

**View logs:**
```bash
az containerapp logs show --name YOUR_APP_NAME --resource-group d2d-rg --follow
```

**Delete everything:**
```bash
az group delete --name d2d-rg --yes
```
