# D2D Linux VM Deployment Information

**Deployment Date:** 2026-01-23
**Status:** ✅ VM Running | ❌ PACS Connectivity Pending

---

## Virtual Machine Details

| Property | Value |
|----------|-------|
| **VM Name** | d2d-vm |
| **VM Type** | Azure Virtual Machine (Linux) |
| **Size** | Standard_B2s (2 vCPU, 4GB RAM) |
| **Operating System** | Ubuntu 22.04 LTS |
| **Location** | Australia Southeast |
| **Resource Group** | d2d-rg |
| **Status** | VM running |

---

## Network Configuration

### IP Addresses
- **Private IP:** 10.200.5.4
- **Public IP:** None (private access only)
- **MAC Address:** 00-22-48-14-7A-B5

### Network Details
| Component | Value |
|-----------|-------|
| **VNet** | vnet-migration |
| **VNet Address Space** | 10.200.0.0/16 |
| **Subnet** | snet-vms |
| **Subnet Range** | 10.200.5.0/24 |
| **Network Security Group** | nsg-d2d-vm |
| **DNS** | Azure Default DNS |

### Security Rules
- **Allow D2D-From-VNet:** Port 8000/TCP from 10.200.0.0/16
- **Default VNet:** Allows all traffic within VNet
- **Internet:** Outbound allowed

---

## D2D Application

### Container Details
- **Container Runtime:** Docker
- **Orchestration:** Docker Compose
- **App Location:** /opt/d2d
- **Container Status:** Running
- **Container Name:** d2d_d2d_1
- **Container IP:** 172.18.0.2 (Docker bridge)

### Application Access
- **Internal URL:** http://10.200.5.4:8000
- **Diagnostics:** http://10.200.5.4:8000/diagnostics
- **API Docs:** http://10.200.5.4:8000/docs

**Note:** Only accessible from within the VNet (10.200.0.0/16)

### Application Directories
```
/opt/d2d/
├── app/                  # Application code
├── static/              # Web interface
├── docker-compose.yml   # Container config
├── Dockerfile          # Container image
├── requirements.txt    # Python dependencies
├── .env                # Environment config
├── uploads/            # Temporary uploads
├── dicom_archive/      # Converted DICOM files
└── destinations.json   # Saved DICOM destinations
```

---

## SSH Access

### Credentials
- **Username:** azureuser
- **SSH Key:** /home/claudeagent/.ssh/id_rsa
- **Key Type:** RSA 4096-bit
- **Key Fingerprint:** SHA256:2HjdgZpyxG6Q/DEDSjJo1eFO6xlaHOYu2xeC5Nd6gjE

### Connecting via SSH

**Option 1: From Another VM in VNet**
```bash
ssh -i /home/claudeagent/.ssh/id_rsa azureuser@10.200.5.4
```

**Option 2: Via Azure Bastion**
```bash
az network bastion ssh \
  --name <bastion-name> \
  --resource-group <bastion-rg> \
  --target-resource-id /subscriptions/13708ff4-5f72-4af3-8b42-cca5dc73e93d/resourceGroups/d2d-rg/providers/Microsoft.Compute/virtualMachines/d2d-vm \
  --auth-type ssh-key \
  --username azureuser \
  --ssh-key /home/claudeagent/.ssh/id_rsa
```

**Option 3: Run Commands Remotely**
```bash
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "your-command-here"
```

---

## Management Commands

### VM Management
```bash
# Start the VM
az vm start --name d2d-vm --resource-group d2d-rg

# Stop the VM (deallocate to save costs)
az vm deallocate --name d2d-vm --resource-group d2d-rg

# Restart the VM
az vm restart --name d2d-vm --resource-group d2d-rg

# Get VM status
az vm get-instance-view --name d2d-vm --resource-group d2d-rg \
  --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv

# Show VM details
az vm show --name d2d-vm --resource-group d2d-rg --show-details
```

### D2D Container Management
```bash
# View container logs
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose logs --tail 100"

# Restart D2D container
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose restart"

# Stop D2D container
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose down"

# Start D2D container
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose up -d"

# Check container status
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose ps"
```

### Update D2D Application
```bash
# Method 1: Rebuild from source
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose down && sudo docker-compose build && sudo docker-compose up -d"

# Method 2: Update code and restart
# (First transfer updated files, then run:)
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose restart"
```

---

## Current Status

### ✅ Working
- [x] VM deployed and running in Australia Southeast
- [x] Correct VNet (10.200.0.0/16) and subnet (10.200.5.0/24)
- [x] Private IP assigned: 10.200.5.4
- [x] Docker and Docker Compose installed
- [x] D2D application container running
- [x] Web interface accessible at http://10.200.5.4:8000 (from VNet)
- [x] NSG configured for port 8000 access

### ❌ Not Working / Pending
- [ ] **PACS Connectivity:** Cannot reach 10.17.1.21:5000
- [ ] **VPN/ExpressRoute:** No connection to on-premises network
- [ ] **Public Access:** No public IP (by design - private only)

---

## Network Connectivity Issue

### Problem
The VM cannot reach the on-premises PACS at **10.17.1.21:5000**

### Root Cause
No network path exists between Azure VNet (10.200.0.0/16) and on-premises network (10.17.1.x)

### Evidence
```bash
# Test from VM shows:
Testing from VM host (10.200.5.4):
FAILED: Cannot connect to PACS

Routes on VM:
default via 10.200.5.1 dev eth0
10.200.5.0/24 dev eth0  # Only local subnet
# No route to 10.17.1.0/24 network
```

### Required Solution
One of the following is needed:

1. **VPN Gateway (Site-to-Site)**
   - Connect Azure VNet to on-premises network
   - Cost: ~$25-140/month
   - Setup time: 30-45 minutes
   - **Recommended for production**

2. **Azure ExpressRoute**
   - Dedicated private connection
   - Cost: ~$50-1000+/month
   - Best performance and reliability
   - **For enterprise deployments**

3. **Point-to-Site VPN**
   - Individual VPN client on VM
   - Lower cost
   - Less reliable
   - **Quick test option**

---

## PACS Configuration (Once Connected)

When VPN/network connectivity is established, configure your PACS to accept connections from:

```
Source Network:  10.200.5.0/24 (d2d VM subnet)
               OR 10.200.0.0/16 (entire Azure VNet)
Destination:     10.17.1.21:5000
Protocol:        TCP (DICOM)
AE Title:        Accept from "D2D_SCU" (configurable in app)
```

---

## Testing Connectivity

### Test PACS from VM
```bash
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "curl -s http://localhost:8000/api/test-pacs | python3 -m json.tool"
```

**Expected when working:**
```json
{
    "target": "10.17.1.21:5000",
    "reachable": true,
    "error_code": 0,
    "message": "Connection successful!"
}
```

**Current result:**
```json
{
    "target": "10.17.1.21:5000",
    "reachable": false,
    "error_code": 11,
    "message": "Connection failed (error code: 11)"
}
```

### Test from D2D Web Interface

Once connectivity is established:

1. Access http://10.200.5.4:8000 (from VNet)
2. Click "DICOM Destinations" → "Add New"
3. Enter:
   - Name: Your PACS Name
   - Host: 10.17.1.21
   - Port: 5000
   - AE Title: (your PACS AE title)
   - Calling AE: D2D_SCU
4. Click "Test Connection"

---

## Cost Estimate

### Monthly Costs
| Resource | Cost |
|----------|------|
| **VM (B2s)** | ~$30-40/month (running 24/7) |
| **Storage (OS Disk)** | ~$5/month (Standard SSD 30GB) |
| **Bandwidth** | Minimal (within Azure) |
| **VPN Gateway** | $0/month (not yet created) |
| **Total Current** | **~$35-45/month** |

### When VPN Added
| VPN Type | Additional Monthly Cost |
|----------|------------------------|
| Basic VPN Gateway | +$25/month |
| VpnGw1 (recommended) | +$140/month |
| ExpressRoute | +$50-1000+/month |

### Cost Saving Options
- **Stop VM when not in use:** Deallocate to pay only storage (~$5/month)
- **Scheduled start/stop:** Run only during business hours
- **Reserved instances:** Save 30-70% with 1-3 year commitment

---

## Next Steps

### Immediate Priority
1. ☐ **Establish VPN/network connectivity** to on-premises (10.17.1.x)
   - Determine if VPN Gateway or ExpressRoute is needed
   - Configure site-to-site VPN
   - Add routes to 10.17.1.0/24 network

2. ☐ **Configure PACS firewall** to accept from 10.200.5.0/24

3. ☐ **Test connectivity** from d2d VM to PACS

4. ☐ **Configure DICOM destination** in d2d app

5. ☐ **Test end-to-end workflow:**
   - Upload PDF/image
   - Convert to DICOM
   - Send to PACS
   - Verify receipt on PACS

### Optional Enhancements
- ☐ Set up Azure Bastion for secure SSH access
- ☐ Configure automatic backups
- ☐ Add monitoring and alerts
- ☐ Set up log aggregation
- ☐ Create VM auto-shutdown schedule
- ☐ Add additional applications/containers as needed

---

## Troubleshooting

### VM Won't Start
```bash
# Check VM status
az vm get-instance-view --name d2d-vm --resource-group d2d-rg

# Check for issues
az vm show --name d2d-vm --resource-group d2d-rg --show-details
```

### Can't Access D2D Web Interface
```bash
# Verify container is running
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "sudo docker ps"

# Check application logs
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose logs --tail 50"

# Test locally on VM
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "curl -I http://localhost:8000"
```

### Container Not Responding
```bash
# Restart container
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose restart"

# Rebuild container (if code changed)
az vm run-command invoke \
  --name d2d-vm \
  --resource-group d2d-rg \
  --command-id RunShellScript \
  --scripts "cd /opt/d2d && sudo docker-compose down && sudo docker-compose build && sudo docker-compose up -d"
```

---

## Support & Documentation

**Related Documentation:**
- `/home/claudeagent/d2d/README.md` - D2D application documentation
- `/home/claudeagent/d2d/DEPLOYMENT-INFO.txt` - Previous Container Apps deployment
- `/home/claudeagent/d2d/PACS-CONNECTIVITY-ISSUE.md` - Network connectivity analysis

**Azure Resources:**
- Subscription ID: `13708ff4-5f72-4af3-8b42-cca5dc73e93d`
- Resource Group: `d2d-rg`
- VNet Resource Group: `rg-migration-vpn`

**Key Files in This Repository:**
- `/home/claudeagent/d2d/VM-DEPLOYMENT-INFO.md` (this file)
- `/home/claudeagent/d2d/cloud-init.yml` - VM initialization script
- `/home/claudeagent/.ssh/id_rsa` - SSH private key for VM access
- `/home/claudeagent/.ssh/id_rsa.pub` - SSH public key

---

## Quick Reference

**VM:** d2d-vm
**IP:** 10.200.5.4
**URL:** http://10.200.5.4:8000
**User:** azureuser
**Key:** ~/.ssh/id_rsa
**Location:** Australia Southeast
**Status:** Running ✅ | PACS Unreachable ❌

---

**Document Generated:** 2026-01-23
**Last Updated:** 2026-01-23
