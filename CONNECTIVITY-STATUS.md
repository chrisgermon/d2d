# D2D Azure Container Instance - Connectivity Status

## Deployment Summary

✓ **Azure Container Instance deployed successfully**
- Name: d2d-aci
- Private IP: **10.200.4.4**
- Subnet: snet-d2d (10.200.4.0/28)
- Location: Australia Southeast
- VNet: vnet-migration (10.200.0.0/16)

## Connectivity Test Results

### Test to PACS (10.17.1.21:5000)
❌ **FAILED** - Error code 11 (Resource temporarily unavailable)

### Network Configuration
```
VNet: vnet-migration (10.200.0.0/16)
  ├── GatewaySubnet (10.200.0.0/27)
  ├── snet-replication (10.200.1.0/24) - Has NIC at 10.200.1.7
  ├── snet-containerapps (10.200.2.0/23)
  └── snet-d2d (10.200.4.0/28) ← D2D Container is here (10.200.4.4)

Target PACS: 10.17.1.21:5000 (Expected to be on-premises)
```

## Critical Issue: No Route to 10.17.1.21

**The container has a private IP (10.200.4.4) but CANNOT reach 10.17.1.21 because:**

1. **10.17.1.21 is NOT in the VNet** (10.200.0.0/16)
   - The container can reach other 10.200.x.x addresses
   - But 10.17.1.x is a different network

2. **No VPN Gateway found** (or not configured)
   - There's a GatewaySubnet but no active VPN gateway
   - No route to on-premises 10.17.1.x network

3. **No VNet Peering found**
   - No peering to another VNet that might have 10.17.1.21

## Questions

**Where is 10.17.1.21 located?**

Is it:
- A) **On-premises** (requires VPN/ExpressRoute from Azure to your network)
- B) **In another Azure VNet** (requires VNet peering)
- C) **In the same data center** but different network segment
- D) **Accessible via internet** with public IP

## Next Steps

### If 10.17.1.21 is On-Premises:

You need a **VPN Gateway** or **ExpressRoute** to connect Azure VNet to your on-premises network:

```bash
# Check if VPN gateway exists
az network vnet-gateway list --resource-group rg-migration-vpn -o table

# If no gateway, you need to create one (takes 30-45 minutes)
az network vnet-gateway create \
  --name vpn-gateway \
  --resource-group rg-migration-vpn \
  --vnet vnet-migration \
  --gateway-type Vpn \
  --vpn-type RouteBased \
  --sku VpnGw1 \
  --location australiasoutheast
```

### If 10.17.1.21 is in Another Azure VNet:

You need **VNet Peering**:

```bash
# Create peering (if you know the other VNet)
az network vnet peering create \
  --name migration-to-pacs \
  --resource-group rg-migration-vpn \
  --vnet-name vnet-migration \
  --remote-vnet /subscriptions/<subscription-id>/resourceGroups/<rg>/providers/Microsoft.Network/virtualNetworks/<vnet-name> \
  --allow-forwarded-traffic
```

### If 10.17.1.21 Has a Public IP:

Test if you can reach it via public IP instead:

```bash
# From the container, test public IP
az container exec --name d2d-aci --resource-group d2d-rg --exec-command "python3 /app/test_pacs_connectivity.py"
# But modify the script to use the public IP
```

## Current Container Status

The D2D container is running and healthy:
- ✓ Has private IP: 10.200.4.4
- ✓ Is in the VNet: vnet-migration
- ✓ Can reach internet (tested)
- ❌ Cannot reach 10.17.1.21 (no route exists)

## To Test Container

Since the container doesn't have a public IP, you can:

1. **From another machine in the VNet** (like 10.200.1.7):
   ```bash
   curl http://10.200.4.4:8000
   ```

2. **Exec into the container**:
   ```bash
   az container exec --name d2d-aci --resource-group d2d-rg --exec-command "/bin/sh"
   ```

3. **View logs**:
   ```bash
   az container logs --name d2d-aci --resource-group d2d-rg --follow
   ```

## Summary

**What's working:**
- ✓ Container deployed with private IP (10.200.4.4)
- ✓ Container is in your VNet
- ✓ Container can reach internet

**What's NOT working:**
- ❌ Cannot reach PACS at 10.17.1.21:5000
- ❌ No VPN/ExpressRoute or peering configured

**What we need to know:**
- How is 10.17.1.21 supposed to be reachable?
- Is there an existing VPN connection we should be using?
- Is 10.17.1.21 actually accessible from Azure?
