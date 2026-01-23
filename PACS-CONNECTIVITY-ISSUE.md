# PACS Connectivity Issue - Resolution Required

## Problem Summary

The D2D container **CANNOT currently reach 10.17.1.21:5000** ❌

## Root Cause

While the Container Apps environment is deployed into the VNet (vnet-migration/snet-containerapps), the **container traffic is still routing through the public internet**, not through the private VNet.

### Evidence:
```
Container IP:    100.100.205.61 (Kubernetes internal)
Outbound IPs:    13.77.3.70, 13.77.0.63, 13.70.186.57 (PUBLIC)
Expected:        10.200.2.x (private VNet)

Test Results:
- Internet (8.8.8.8:53):     ✓ SUCCESS
- PACS (10.17.1.21:5000):    ✗ FAILED (error code 11)
```

## Why This Happens

Azure Container Apps VNet integration configures the **infrastructure** in the VNet, but **outbound container traffic** still uses Azure's public network by default. This is different from Azure Container Instances or VMs which get direct VNet connectivity.

## Solutions

### Option 1: Deploy Azure Container Instance (ACI) - RECOMMENDED ✓

**Pros:**
- Gets a true private IP from VNet
- Direct VNet connectivity (can reach 10.17.1.21)
- Still containerized, similar to Container Apps

**Cons:**
- No auto-scaling (single instance)
- Manual restart required for updates
- ~$30-40/month (always running)

**Command:**
```bash
# Create a dedicated subnet for ACI (can't use snet-replication)
az network vnet subnet create \
  --vnet-name vnet-migration \
  --resource-group rg-migration-vpn \
  --name snet-d2d \
  --address-prefixes 10.200.4.0/28 \
  --delegations Microsoft.ContainerInstance/containerGroups

# Deploy container with private IP
az container create \
  --name d2d-aci \
  --resource-group d2d-rg \
  --image d2dacr9129522.azurecr.io/d2d:latest \
  --registry-login-server d2dacr9129522.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --vnet /subscriptions/<subscription-id>/resourceGroups/rg-migration-vpn/providers/Microsoft.Network/virtualNetworks/vnet-migration \
  --subnet snet-d2d \
  --os-type Linux \
  --cpu 1 \
  --memory 2 \
  --ports 8000 \
  --environment-variables HOST=0.0.0.0 PORT=8000 \
  --location australiasoutheast

# You'll get an IP like 10.200.4.4 that CAN reach 10.17.1.21
```

### Option 2: Deploy Azure VM

**Pros:**
- Full VNet integration
- Complete control
- Can install anything

**Cons:**
- More expensive (~$50-100/month)
- Manual OS management
- Overkill for a simple container

### Option 3: Use Azure App Service with VNet Integration

**Pros:**
- Managed service
- VNet integration available
- Similar to Container Apps

**Cons:**
- More expensive than Container Apps
- Still may have outbound routing issues
- Less flexible than containers

### Option 4: Keep Container Apps + VPN Client on Container

**Pros:**
- Keep current setup
- No infrastructure changes

**Cons:**
- Complex setup
- VPN client in container is not ideal
- Defeats purpose of VNet integration

## Recommended Next Steps

### Immediate: Deploy as Azure Container Instance

1. Create new subnet for ACI:
   ```bash
   az network vnet subnet create \
     --vnet-name vnet-migration \
     --resource-group rg-migration-vpn \
     --name snet-d2d \
     --address-prefixes 10.200.4.0/28 \
     --delegations Microsoft.ContainerInstance/containerGroups
   ```

2. Deploy D2D as ACI (see Option 1 commands above)

3. Access via private IP (10.200.4.x) from your network

4. Test PACS connectivity - it WILL work

### Trade-offs:

| Feature | Container Apps (Current) | Container Instance (Proposed) |
|---------|-------------------------|-------------------------------|
| Can reach PACS (10.17.1.21) | ✗ NO | ✓ YES |
| Auto-scaling | ✓ Yes (0-2) | ✗ No (single instance) |
| Cost (idle) | ~$0/month | ~$30/month |
| Public HTTPS URL | ✓ Yes | ✗ No (private only) |
| VNet IP | ✗ No | ✓ Yes (10.200.4.x) |
| Update process | Automatic | Manual restart |

## Testing the Diagnostics Page

Access the diagnostics tool:
**https://d2d-app-vnet.kindglacier-71e74fc9.australiasoutheast.azurecontainerapps.io/diagnostics**

This page will show:
- Current network info
- Connectivity tests to various IPs
- Test results for PACS connection

## Current Status

- App deployed: ✓ YES
- VNet configured: ✓ YES (infrastructure only)
- Can reach internet: ✓ YES
- Can reach PACS: ✗ NO (traffic routes via public internet)

## Decision Needed

Do you want to:
1. **Switch to Azure Container Instance** - Gets private IP, can reach PACS, but no auto-scaling
2. **Deploy an Azure VM** - Full control, can reach PACS, but more expensive
3. **Keep investigating** Container Apps routing configuration (may not be possible)

Let me know which direction you'd like to go!
