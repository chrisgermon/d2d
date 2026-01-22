#!/bin/bash
# Script to find existing Azure VNet details for D2D deployment

echo "=== Azure VNet Discovery Tool ==="
echo ""
echo "This will help you find your existing VNet details for D2D deployment"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Install it first:"
    echo "   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Login check
echo "Checking Azure login status..."
az account show &> /dev/null
if [ $? -ne 0 ]; then
    echo "Please login to Azure:"
    az login
fi

# Get current subscription
SUBSCRIPTION=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo ""
echo "✅ Connected to subscription: $SUBSCRIPTION"
echo "   Subscription ID: $SUBSCRIPTION_ID"
echo ""

# List all VNets
echo "=== Finding Virtual Networks ==="
echo ""

VNETS=$(az network vnet list --query "[].{Name:name, ResourceGroup:resourceGroup, Location:location, AddressSpace:addressSpace.addressPrefixes[0]}" -o tsv)

if [ -z "$VNETS" ]; then
    echo "❌ No Virtual Networks found in this subscription"
    echo ""
    echo "You'll need to create a new VNet or use a different subscription."
    exit 1
fi

echo "Found Virtual Networks:"
echo ""
printf "%-5s %-30s %-25s %-20s %-20s\n" "NUM" "VNET NAME" "RESOURCE GROUP" "LOCATION" "ADDRESS SPACE"
echo "────────────────────────────────────────────────────────────────────────────────────────────────────"

counter=1
declare -A vnet_map
declare -A rg_map
declare -A location_map

while IFS=$'\t' read -r name rg location addr; do
    printf "%-5s %-30s %-25s %-20s %-20s\n" "$counter" "$name" "$rg" "$location" "$addr"
    vnet_map[$counter]=$name
    rg_map[$counter]=$rg
    location_map[$counter]=$location
    ((counter++))
done <<< "$VNETS"

echo ""
echo "Select a VNet (enter number):"
read -r VNET_NUM

if [ -z "${vnet_map[$VNET_NUM]}" ]; then
    echo "❌ Invalid selection"
    exit 1
fi

SELECTED_VNET=${vnet_map[$VNET_NUM]}
SELECTED_RG=${rg_map[$VNET_NUM]}
SELECTED_LOCATION=${location_map[$VNET_NUM]}

echo ""
echo "✅ Selected: $SELECTED_VNET"
echo ""

# Check for VPN Gateway
echo "=== Checking VPN Configuration ==="
echo ""

VPN_GATEWAY=$(az network vnet-gateway list --resource-group $SELECTED_RG --query "[?contains(@.name, 'vpn') || contains(@.name, 'gateway')].{Name:name, Type:gatewayType, State:provisioningState}" -o tsv 2>/dev/null)

if [ -z "$VPN_GATEWAY" ]; then
    echo "⚠️  No VPN Gateway found in resource group: $SELECTED_RG"
    echo ""
    echo "Checking for ExpressRoute or other connectivity..."

    # Check for ExpressRoute
    EXPRESS_ROUTE=$(az network express-route list --resource-group $SELECTED_RG --query "[].{Name:name, State:circuitProvisioningState}" -o tsv 2>/dev/null)

    if [ -z "$EXPRESS_ROUTE" ]; then
        echo "⚠️  No ExpressRoute found either"
        echo ""
        echo "This VNet may not have connectivity to on-premises networks."
        echo "Do you want to continue anyway? (y/n)"
        read -r CONTINUE
        if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ Found ExpressRoute Circuit:"
        echo "$EXPRESS_ROUTE"
    fi
else
    echo "✅ Found VPN Gateway:"
    while IFS=$'\t' read -r name type state; do
        echo "   Name: $name"
        echo "   Type: $type"
        echo "   State: $state"
    done <<< "$VPN_GATEWAY"
fi

echo ""

# List subnets
echo "=== Available Subnets ==="
echo ""

SUBNETS=$(az network vnet subnet list --resource-group $SELECTED_RG --vnet-name $SELECTED_VNET --query "[].{Name:name, AddressPrefix:addressPrefix}" -o tsv)

echo "Subnets in $SELECTED_VNET:"
echo ""
printf "%-5s %-30s %-20s\n" "NUM" "SUBNET NAME" "ADDRESS PREFIX"
echo "───────────────────────────────────────────────────────────────"

counter=1
declare -A subnet_map

while IFS=$'\t' read -r name prefix; do
    # Skip GatewaySubnet (reserved for VPN Gateway)
    if [ "$name" != "GatewaySubnet" ]; then
        printf "%-5s %-30s %-20s\n" "$counter" "$name" "$prefix"
        subnet_map[$counter]=$name
        ((counter++))
    fi
done <<< "$SUBNETS"

echo ""
echo "Select a subnet for D2D (enter number):"
read -r SUBNET_NUM

if [ -z "${subnet_map[$SUBNET_NUM]}" ]; then
    echo "❌ Invalid selection"
    exit 1
fi

SELECTED_SUBNET=${subnet_map[$SUBNET_NUM]}

echo ""
echo "=== ✅ Configuration Found! ==="
echo ""
echo "VNet Details:"
echo "────────────────────────────────────────"
echo "Resource Group:  $SELECTED_RG"
echo "VNet Name:       $SELECTED_VNET"
echo "Subnet Name:     $SELECTED_SUBNET"
echo "Location:        $SELECTED_LOCATION"
echo ""

# Generate configuration
CONFIG_FILE="/tmp/d2d-azure-config.txt"
cat > $CONFIG_FILE << EOF
# Azure VNet Configuration for D2D Deployment
# Copy these values to deploy-to-azure.sh

USE_EXISTING_VNET="yes"
EXISTING_VNET_RG="$SELECTED_RG"
EXISTING_VNET_NAME="$SELECTED_VNET"
EXISTING_SUBNET_NAME="$SELECTED_SUBNET"

# Also update LOCATION if different:
LOCATION="$SELECTED_LOCATION"

# Subscription ID (for reference):
# $SUBSCRIPTION_ID
EOF

echo "Configuration saved to: $CONFIG_FILE"
echo ""
echo "=== Next Steps ==="
echo ""
echo "1. Copy configuration to deployment script:"
echo "   nano /opt/d2d/deploy-to-azure.sh"
echo ""
echo "2. Replace the CONFIGURATION section with:"
echo ""
cat $CONFIG_FILE
echo ""
echo "3. Run deployment:"
echo "   cd /opt/d2d"
echo "   ./deploy-to-azure.sh"
echo ""
echo "=== Test PACS Connectivity ==="
echo ""
echo "After deployment, test if your PACS is reachable:"
echo ""
echo "# From an Azure VM in the same VNet or Azure Cloud Shell:"
echo "sudo apt install dcmtk"
echo "echoscu -aet D2D_SCU -aec YOUR_PACS_AE YOUR_PACS_IP YOUR_PACS_PORT"
echo ""

# Copy config to clipboard if possible
if command -v xclip &> /dev/null; then
    cat $CONFIG_FILE | xclip -selection clipboard
    echo "✅ Configuration copied to clipboard!"
elif command -v pbcopy &> /dev/null; then
    cat $CONFIG_FILE | pbcopy
    echo "✅ Configuration copied to clipboard!"
fi
