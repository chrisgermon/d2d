# D2D Network Configuration & PACS Connectivity

## Current Network Setup

### Container App Network Details
- **Container App Name:** d2d-app-vnet
- **Resource Group:** d2d-rg
- **Location:** Australia Southeast
- **URL:** https://d2d-app-vnet.kindglacier-71e74fc9.australiasoutheast.azurecontainerapps.io

### VNet Integration
- **VNet:** vnet-migration (10.200.0.0/16)
- **Container Subnet:** snet-containerapps (10.200.2.0/23)
- **Delegation:** Microsoft.App/environments

**Network Architecture:**
```
Your PACS (10.17.1.21:5000)
          ↕ (via VPN/ExpressRoute)
vnet-migration (10.200.0.0/16)
          ├── GatewaySubnet (10.200.0.0/27)
          ├── snet-replication (10.200.1.0/24) - IN USE, can't delegate
          └── snet-containerapps (10.200.2.0/23) - D2D containers here
                    ↕
              D2D Container App
```

## Static IP Limitation

**Question:** Can the container get a static IP on 10.200.1.0/24?

**Answer:** Not directly with Azure Container Apps because:

1. **Container Apps don't provide static private IPs**
   - Containers use ephemeral IPs from the subnet pool (10.200.2.0/23)
   - Each container instance may get a different IP
   - IPs are managed by the platform, not assignable

2. **10.200.1.0/24 subnet is in use**
   - Already has resources (vrg-replication-server791)
   - Cannot be delegated to Container Instances
   - Cannot mix delegated and non-delegated resources

## Connectivity Status

### What WORKS:
✓ Container can make **outbound connections** to 10.17.1.21:5000
✓ Source IP will be from 10.200.2.0/23 range
✓ PACS will see connections coming from 10.200.2.x addresses

### What DOESN'T work:
✗ No fixed/static private IP for the container
✗ Incoming connections to a specific IP (use the public URL instead)

## PACS Configuration

### On Your PACS:
You need to **allow connections from 10.200.2.0/23** subnet:
- Add firewall rule: Allow 10.200.2.0/23 → 10.17.1.21:5000
- Add AE Title: D2D_SCU (or configure in the app)
- The source IP will vary within 10.200.2.0-10.200.3.255 range

## Testing PACS Connectivity

### From your network (to verify PACS is accessible):
```bash
# From a machine on 10.200.1.0/24 network:
nc -zv 10.17.1.21 5000
# Or with DICOM tools:
echoscu -aet D2D_SCU -aec YOUR_PACS_AE 10.17.1.21 5000
```

### From the D2D app:
1. Go to: https://d2d-app-vnet.kindglacier-71e74fc9.australiasoutheast.azurecontainerapps.io
2. Click "DICOM Destinations"
3. Add destination:
   - Name: Your PACS
   - Host: 10.17.1.21
   - Port: 5000
   - AE Title: (your PACS AE title)
   - Calling AE: D2D_SCU
4. Click "Test Connection"

## Known Issue: DICOM Echo Error

**Problem:** The DICOM verify/test endpoint returns 500 Internal Server Error

**Possible Causes:**
1. Network timeout (PACS not reachable)
2. PACS rejecting connection from 10.200.2.x subnet
3. Wrong AE titles
4. Firewall blocking connection

**To Debug:**
Check the container logs:
```bash
az containerapp logs show --name d2d-app-vnet --resource-group d2d-rg --follow
```

Then try to test connection from the web interface and watch the logs.

## Alternative: Static IP with Azure Container Instances

If you **absolutely need** a static IP on 10.200.1.x:

### Option A: Use a Different Subnet
Create a new /28 subnet:
```bash
az network vnet subnet create \
  --vnet-name vnet-migration \
  --resource-group rg-migration-vpn \
  --name snet-d2d \
  --address-prefixes 10.200.4.0/28 \
  --delegations Microsoft.ContainerInstance/containerGroups
```

Then deploy as Azure Container Instance (ACI) instead of Container Apps.

### Option B: Use Azure VM
Deploy a small Linux VM that gets a static IP from any subnet you choose.

### Option C: Use Network Profile
Create a network profile that assigns specific IPs, but this is complex and not recommended.

## Recommended Configuration

**For most use cases, the current setup is optimal:**

1. ✅ Container Apps (current setup)
   - Auto-scaling (0-2 replicas)
   - Cost-effective ($0-10/month)
   - VNet integrated (can reach PACS)
   - HTTPS endpoint
   - Automatic updates

2. Configure PACS to accept from subnet:
   - Allow source: 10.200.2.0/23
   - Destination: 10.17.1.21:5000
   - Protocol: TCP (DICOM)

3. If static IP is critical, switch to Azure Container Instance or VM

## Next Steps

1. **Verify PACS is configured to accept connections from 10.200.2.0/23**
2. **Test connectivity** using the D2D web interface
3. **Check firewall rules** between Azure VNet and your PACS
4. **Review logs** if connection fails

## Support Commands

```bash
# View logs
az containerapp logs show --name d2d-app-vnet --resource-group d2d-rg --follow

# Restart container
az containerapp revision restart --name d2d-app-vnet --resource-group d2d-rg

# Check VNet integration
az containerapp env show --name d2d-env-vnet --resource-group d2d-rg --query vnetConfiguration

# List all resources
az resource list --resource-group d2d-rg -o table
```
