# D2D Public IP Deployment

## ⚠️ Security Notice

D2D is now accessible via a **public IP address** to enable access from VRG Hub hosted on Lovable/Cloudflare.

**IMPORTANT:** This configuration exposes D2D to the internet. Please implement additional security measures as soon as possible.

---

## Current Configuration

### Network Details
- **Public IP:** 4.198.108.152
- **Port:** 8000 (HTTP - unencrypted)
- **Access:** Available from anywhere on the internet
- **URL:** http://4.198.108.152:8000

### Azure Resources
- **VM:** d2d-vm
- **Resource Group:** VRG-PAX8
- **Location:** Australia Southeast
- **Subscription:** Azure Pax8
- **Public IP Resource:** d2d-vm-public-ip (Static)

### Network Security Group (NSG)
**NSG Name:** d2d-vmNSG

**Current Rules:**
| Priority | Name | Port | Source | Access | Description |
|----------|------|------|--------|--------|-------------|
| 1000 | default-allow-ssh | 22 | * | Allow | SSH access |
| 1010 | allow-d2d-http | 8000 | * | Allow | D2D application |

⚠️ **Security Risk:** Port 8000 is open to all IP addresses (*)

---

## VRG Hub Integration

### Development (Lovable Preview)
Uses vite proxy in `vite.config.ts`:
```typescript
proxy: {
  '/d2d': {
    target: 'http://4.198.108.152:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/d2d/, ''),
    ws: true,
  },
}
```

### Production (hub.visionradiology.com.au)
D2dConverter component automatically detects environment:
- **Development:** Uses `/d2d/` proxy
- **Production:** Uses direct URL `http://4.198.108.152:8000`

Can override with environment variable:
```bash
VITE_D2D_URL=http://4.198.108.152:8000
```

---

## 🔒 Urgent Security Improvements Needed

### 1. Implement HTTPS (SSL/TLS)
**Current:** HTTP (unencrypted) - PHI transmitted in plaintext
**Required:** HTTPS with valid SSL certificate

**Options:**
- **Let's Encrypt** (Free, automated)
- **Azure Certificate** (if using App Gateway)
- **Commercial SSL Certificate**

**Implementation with Let's Encrypt:**
```bash
# Install Certbot
sudo apt update
sudo apt install certbot

# Generate certificate (requires DNS or HTTP validation)
sudo certbot certonly --standalone -d d2d.visionradiology.com.au

# Configure nginx as reverse proxy with SSL
# Certificate auto-renews via cron
```

### 2. Add Authentication
**Current:** No authentication - anyone can access
**Required:** User authentication for all routes

**Options:**
- HTTP Basic Authentication (simple, browser built-in)
- API Key Authentication (for programmatic access)
- OAuth 2.0 / OIDC (integrate with existing SSO)
- Azure AD Authentication

**Quick Implementation - Basic Auth:**
See `AUTHENTICATION-GUIDE.md` for implementation details.

### 3. IP Whitelisting
**Current:** Accessible from any IP address
**Recommended:** Restrict to known IPs

**Update NSG Rule:**
```bash
# Remove current rule
az network nsg rule delete \
  --resource-group VRG-PAX8 \
  --nsg-name d2d-vmNSG \
  --name allow-d2d-http

# Add restricted rule (example IPs)
az network nsg rule create \
  --resource-group VRG-PAX8 \
  --nsg-name d2d-vmNSG \
  --name allow-d2d-http-restricted \
  --priority 1010 \
  --source-address-prefixes 185.158.133.1 <other-trusted-IPs> \
  --destination-port-ranges 8000 \
  --access Allow \
  --protocol Tcp \
  --description "D2D access from trusted IPs only"
```

**Get VRG Hub IPs:**
```bash
# Find IPs that hub.visionradiology.com.au uses
nslookup hub.visionradiology.com.au
dig hub.visionradiology.com.au +short
```

### 4. Rate Limiting
Implement rate limiting to prevent abuse:
- Use nginx as reverse proxy with rate limiting
- Use Azure Application Gateway with WAF
- Implement in FastAPI application

### 5. Web Application Firewall (WAF)
Deploy Azure Application Gateway with WAF to protect against:
- SQL injection
- Cross-site scripting (XSS)
- DDoS attacks
- OWASP Top 10 vulnerabilities

### 6. Audit Logging
Implement comprehensive logging:
- All access attempts (successful and failed)
- All API calls with user context
- All DICOM operations (send, query, convert)
- PHI access tracking

### 7. Regular Security Scans
- Vulnerability scanning
- Penetration testing
- Dependency updates (python packages)
- Security patches for OS

---

## Compliance Considerations

### PHI/HIPAA Compliance
- **Encryption in Transit:** ❌ Not implemented (HTTP)
- **Encryption at Rest:** ⚠️ Check disk encryption
- **Access Controls:** ❌ No authentication
- **Audit Logs:** ⚠️ Limited logging
- **Data Minimization:** ✅ Only necessary data stored

### Australian Privacy Act
- D2D processes health information
- Must comply with Australian Privacy Principles (APPs)
- Requires appropriate security measures

### Recommendations:
1. **URGENT:** Implement HTTPS within 48 hours
2. **HIGH:** Add authentication within 1 week
3. **MEDIUM:** IP whitelisting within 2 weeks
4. **MEDIUM:** WAF deployment within 1 month
5. **ONGOING:** Regular security audits

---

## Current Risks

| Risk | Severity | Impact | Likelihood | Mitigation Status |
|------|----------|--------|------------|-------------------|
| Unencrypted PHI transmission | **CRITICAL** | Data breach, compliance violation | High | ❌ None |
| No authentication | **HIGH** | Unauthorized access, data tampering | High | ❌ None |
| Public internet exposure | **HIGH** | Attack surface, DDoS | Medium | ⚠️ NSG only |
| No rate limiting | **MEDIUM** | Resource exhaustion, abuse | Medium | ❌ None |
| No WAF | **MEDIUM** | Application exploits | Low | ❌ None |

---

## Monitoring

### Current Monitoring
- Azure VM metrics (CPU, memory, disk)
- Network traffic statistics
- Basic application logs

### Recommended Monitoring
- **Azure Monitor:** VM and network metrics
- **Log Analytics:** Centralized logging
- **Application Insights:** Application performance
- **Security Center:** Security recommendations
- **Sentinel:** Security information and event management (SIEM)

### Key Metrics to Track
- Request rate (requests/minute)
- Error rate (4xx, 5xx responses)
- Response time
- Concurrent connections
- Failed authentication attempts (once implemented)
- DICOM operations (conversions, sends, queries)

---

## Cost Considerations

### Current Monthly Costs (Estimated)
- **VM (D2s_v3):** ~$150 AUD/month
- **Public IP (Static):** ~$5 AUD/month
- **Bandwidth:** Variable (minimal for low usage)
- **Storage:** Included in VM
- **Total:** ~$155 AUD/month

### Additional Costs for Security
- **SSL Certificate:** Free (Let's Encrypt) or ~$50-200/year
- **Application Gateway + WAF:** ~$300 AUD/month
- **Azure AD Authentication:** May be included in existing license
- **Log Analytics:** ~$3-10/GB ingested
- **Security Center:** May be included in subscription

---

## Rollback Plan

If issues arise, you can remove public IP access:

```bash
# Remove public IP from VM
az network nic ip-config update \
  --resource-group VRG-PAX8 \
  --nic-name d2d-vmVMNic \
  --name ipconfigd2d-vm \
  --remove publicIPAddress

# Delete public IP resource
az network public-ip delete \
  --resource-group VRG-PAX8 \
  --name d2d-vm-public-ip

# Revert VRG Hub to use private IP (requires moving to Azure)
# Edit vite.config.ts: target: 'http://10.200.1.8:8000'
```

---

## Next Steps

### Immediate (This Week)
1. ✅ Assign public IP to D2D VM
2. ✅ Update VRG Hub configuration
3. ✅ Test integration from hub.visionradiology.com.au
4. ⏳ Implement HTTPS with Let's Encrypt
5. ⏳ Add basic authentication

### Short Term (This Month)
6. ⏳ IP whitelisting (restrict to VRG Hub IPs)
7. ⏳ Set up comprehensive logging
8. ⏳ Implement rate limiting
9. ⏳ Security audit

### Long Term (Next 3 Months)
10. ⏳ Deploy Azure Application Gateway + WAF
11. ⏳ Integrate with Azure AD authentication
12. ⏳ Compliance review and documentation
13. ⏳ Regular penetration testing

---

## Support and Documentation

**Related Documentation:**
- `/home/claudeagent/d2d/VM-DEPLOYMENT-INFO.md` - VM deployment details
- `/home/claudeagent/d2d/WORKLIST-FEATURE.md` - Worklist functionality
- `/home/claudeagent/vrg-hub/D2D-INTEGRATION.md` - VRG Hub integration

**Azure Resources:**
- VM: `az vm show --name d2d-vm --resource-group VRG-PAX8`
- NSG: `az network nsg show --name d2d-vmNSG --resource-group VRG-PAX8`
- Public IP: `az network public-ip show --name d2d-vm-public-ip --resource-group VRG-PAX8`

**Testing:**
```bash
# Test HTTP access
curl http://4.198.108.152:8000/

# Test from VRG Hub
curl https://hub.visionradiology.com.au/d2d-converter

# Check D2D logs
ssh azureuser@4.198.108.152
cd /opt/d2d
sudo docker-compose logs -f
```

---

**Document Created:** 2026-01-23
**Last Updated:** 2026-01-23
**Status:** 🟡 Active with Security Warnings
**Action Required:** Implement HTTPS and Authentication URGENTLY
