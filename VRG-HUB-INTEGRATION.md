# D2D Integration with VRG Hub - Quick Reference

## ✅ Integration Complete!

D2D is now embedded in VRG Hub and accessible from anywhere users can access VRG Hub.

## Access URLs

### Through VRG Hub (Recommended)
- **Primary:** `https://your-vrg-hub.com/d2d-converter`
- **Alternative:** `https://your-vrg-hub.com/documents-to-dicom`

### Direct Access (Private Network Only)
- **Direct:** `http://10.200.1.8:8000`

## How It Works

```
┌─────────────┐         ┌──────────────┐         ┌────────────┐
│   User      │────────▶│   VRG Hub    │────────▶│ D2D Backend│
│ (Anywhere)  │         │  (Public)    │         │ (10.200.1.8)│
└─────────────┘         └──────────────┘         └────────────┘
                              │                         │
                         Reverse Proxy              Docker
                         (vite config)              Container
```

## What Users See

1. **Login to VRG Hub** (normal authentication)
2. **Navigate to D2D Converter** page
3. **Full D2D interface** embedded in VRG Hub
4. **All features work** exactly the same:
   - Document conversion
   - Worklist query
   - DICOM send to PACS
   - Archive management

## Technical Details

### Files Modified in VRG Hub

**1. vite.config.ts**
- Added reverse proxy for `/d2d/*` routes
- Forwards to `http://10.200.1.8:8000`
- Handles WebSocket connections

**2. src/pages/D2dConverter.tsx** (NEW)
- Responsive page component
- Embeds D2D via iframe
- Loading states and error handling
- Quick start guide

**3. src/App.tsx**
- Added routes for D2D converter
- Lazy-loaded component
- Two URL paths available

### Proxy Configuration

```typescript
proxy: {
  '/d2d': {
    target: 'http://10.200.1.8:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/d2d/, ''),
    ws: true,
  },
}
```

## Benefits

### For Users
✅ **Access from anywhere** - Don't need VPN or private network access
✅ **Single sign-on** - Log into VRG Hub once
✅ **Familiar interface** - Same VRG Hub UI/UX
✅ **Mobile friendly** - Works on tablets and phones
✅ **No training needed** - Same D2D interface they know

### For IT
✅ **Centralized access** - All through VRG Hub
✅ **Better security** - D2D not exposed to internet
✅ **Easier management** - One portal to maintain
✅ **Audit logging** - Track usage through VRG Hub
✅ **No firewall changes** - Uses existing VRG Hub access

## Network Requirements

**VRG Hub Server:**
- Must be able to reach 10.200.1.8:8000
- Same VNet or VPN/peering configured
- Outbound connections to d2d-vm allowed

**D2D VM:**
- Running at 10.200.1.8:8000
- Accessible from VRG Hub server IP
- Connected to PACS (10.17.1.21:5000)
- Connected to Worklist (10.17.1.21:5010)

**Users:**
- Access VRG Hub (public URL)
- No direct network access to 10.200.1.8 needed
- Standard browser (Chrome, Edge, Safari)

## Production Deployment

### Nginx (if VRG Hub uses nginx)

Add to nginx config:

```nginx
location /d2d/ {
    proxy_pass http://10.200.1.8:8000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

### Apache (if VRG Hub uses Apache)

```apache
ProxyPass /d2d/ http://10.200.1.8:8000/
ProxyPassReverse /d2d/ http://10.200.1.8:8000/
```

## Testing

### 1. Development Test

```bash
cd /home/claudeagent/vrg-hub
npm run dev
# Navigate to: http://localhost:8080/d2d-converter
```

### 2. Verify Proxy

```bash
# From VRG Hub server
curl http://10.200.1.8:8000
# Should return D2D HTML
```

### 3. End-to-End Test

1. Access VRG Hub
2. Navigate to `/d2d-converter`
3. D2D interface should load
4. Test worklist query
5. Upload and convert a document
6. Verify PACS send works

## Monitoring

### Health Check

```bash
# Check D2D is accessible from VRG Hub
curl -I http://10.200.1.8:8000
```

### Logs

**VRG Hub:**
- Browser console for client errors
- Server logs for proxy issues

**D2D:**
```bash
ssh azureuser@10.200.1.8
cd /opt/d2d
sudo docker-compose logs --tail 100
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| D2D not loading | Check d2d-vm is running & accessible from VRG Hub server |
| CORS errors | Verify `changeOrigin: true` in proxy config |
| 404 on /d2d/ | Restart VRG Hub dev server or check nginx/Apache config |
| Blank iframe | Check D2D container is running: `docker-compose ps` |

## Next Steps

1. **Deploy to Production**
   - Update nginx/Apache config
   - Test from production VRG Hub URL
   - Verify all features work

2. **Train Users**
   - Show new D2D location in VRG Hub
   - Same features, new access method
   - Emphasize "works from anywhere"

3. **Monitor Usage**
   - Check VRG Hub access logs
   - Monitor D2D container logs
   - Track conversion success rates

## Support

**For D2D Integration Issues:**
- Check `/home/claudeagent/vrg-hub/D2D-INTEGRATION.md`
- Verify network connectivity to 10.200.1.8

**For D2D Application Issues:**
- Check `/home/claudeagent/d2d/WORKLIST-FEATURE.md`
- Check `/home/claudeagent/d2d/VM-DEPLOYMENT-INFO.md`

**For VRG Hub Issues:**
- Standard VRG Hub support procedures

---

## Summary

🎉 **D2D is now integrated with VRG Hub!**

Users can access the full D2D functionality from anywhere through VRG Hub, without needing direct access to the private network.

**Key URLs:**
- VRG Hub D2D: `https://your-vrg-hub.com/d2d-converter`
- Direct D2D: `http://10.200.1.8:8000` (private only)
- GitHub (D2D): `https://github.com/chrisgermon/d2d`

**Status:** ✅ Ready for deployment

---

**Document Created:** 2026-01-23
**Last Updated:** 2026-01-23
