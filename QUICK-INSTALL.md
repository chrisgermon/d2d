# D2D Quick Installation Guide

Get D2D up and running in 5 minutes.

## Prerequisites

- Ubuntu 22.04 or 24.04 LTS
- sudo access
- Internet connection (for initial setup)

## Installation

### Option 1: One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/chrisgermon/d2d/master/install-ubuntu.sh | sudo bash
```

### Option 2: Manual Install

```bash
# Download installer
wget https://raw.githubusercontent.com/chrisgermon/d2d/master/install-ubuntu.sh

# Make executable
chmod +x install-ubuntu.sh

# Run installer
sudo ./install-ubuntu.sh
```

The installer will:
- ✓ Install all dependencies (Python, Poppler, ImageMagick)
- ✓ Clone D2D from GitHub
- ✓ Set up Python virtual environment
- ✓ Create systemd service
- ✓ Configure firewall
- ✓ Start D2D automatically

## Post-Installation

### 1. Change API Key (Important!)

```bash
sudo nano /opt/d2d/.env
```

Change the line:
```
D2D_API_KEYS=vrg-d2d-secure-key-2026-change-this-now
```

To a secure random string.

Then restart:
```bash
sudo systemctl restart d2d
```

### 2. Access Web Interface

Open browser to:
```
http://YOUR_SERVER_IP:8000
```

Replace `YOUR_SERVER_IP` with your server's IP address.

### 3. Configure PACS Destination

1. Click "DICOM Destinations" button
2. Click "Add New Destination"
3. Enter your PACS details:
   - Name: `Intelerad PACS` (or your PACS name)
   - AE Title: `AURVCMOD1` (your PACS AE title)
   - Host: `10.17.1.21` (your PACS IP)
   - Port: `5000` (your PACS port)
   - Calling AE: `D2D_SCU`
4. Click "Save"
5. Click "Test Connection" to verify

## Connect from Claude Code

### Option 1: SSH Tunnel (Easiest)

From your local machine:

```bash
ssh -L 8000:localhost:8000 user@your-d2d-server-ip
```

Now access D2D at `http://localhost:8000` from Claude Code.

### Option 2: MCP Server (Best Integration)

1. **On D2D server**, install MCP dependencies:

```bash
cd /opt/d2d/mcp-server
sudo npm install
```

2. **On your local machine**, configure Claude Code:

Edit `~/.config/claude/mcp.json` (create if doesn't exist):

```json
{
  "mcpServers": {
    "d2d": {
      "command": "ssh",
      "args": [
        "user@your-d2d-server-ip",
        "cd /opt/d2d/mcp-server && D2D_API_URL=http://localhost:8000 node index.js"
      ]
    }
  }
}
```

3. Restart Claude Code

Now you can say things like:
- "Upload this PDF to D2D for patient Smith^John with ID 12345"
- "List DICOM destinations"
- "Send the latest file to Intelerad PACS"

### Option 3: CLI Script

```bash
# Copy CLI script to local machine
scp user@d2d-server:/opt/d2d/d2d-cli.sh ~/d2d-cli.sh
chmod +x ~/d2d-cli.sh

# Set D2D URL (if using SSH tunnel)
export D2D_URL=http://localhost:8000

# Use it
./d2d-cli.sh status
./d2d-cli.sh upload document.pdf "Doe^John" "12345"
```

## Common Commands

```bash
# Check service status
sudo systemctl status d2d

# View logs
sudo journalctl -u d2d -f

# Restart service
sudo systemctl restart d2d

# Stop service
sudo systemctl stop d2d

# Start service
sudo systemctl start d2d
```

## Test Your Installation

### 1. Test Web Interface

```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{"status": "healthy", "version": "1.0.0"}
```

### 2. Test PACS Connectivity

```bash
# Test network connection to PACS
nc -zv 10.17.1.21 5000

# Should show: Connection succeeded!
```

### 3. Upload Test File

1. Go to web interface: `http://YOUR_SERVER_IP:8000`
2. Drag and drop a PDF or image
3. Fill in patient details
4. Click "Convert to DICOM"
5. Should see success message

### 4. Send to PACS (Optional)

1. After converting a file
2. Select destination from dropdown
3. Click "Send to PACS"
4. Check PACS to verify receipt

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u d2d -n 50 --no-pager

# Try running manually
cd /opt/d2d
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Can't Access Web Interface

```bash
# Check if service is running
sudo systemctl status d2d

# Check if port is listening
sudo netstat -tulpn | grep 8000

# Check firewall
sudo ufw status
sudo ufw allow 8000/tcp
```

### PACS Connection Fails

```bash
# Test network connectivity
ping 10.17.1.21

# Test DICOM port
nc -zv 10.17.1.21 5000

# Check if PACS allows your IP
# Contact PACS administrator to whitelist your D2D server IP
```

### PDF Conversion Fails

```bash
# Check ImageMagick configuration
cat /etc/ImageMagick-6/policy.xml | grep PDF

# Should show: rights="read|write"
# If not, re-run installer or manually fix:
sudo sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml
sudo systemctl restart d2d
```

## Next Steps

1. Read full documentation: `/opt/d2d/README.md`
2. Configure worklist integration: `/opt/d2d/WORKLIST-FEATURE.md`
3. Set up HTTPS with Nginx: `/opt/d2d/ONPREM-DEPLOYMENT.md`
4. Configure backups
5. Set up monitoring

## Support

- **GitHub**: https://github.com/chrisgermon/d2d/issues
- **Logs**: `sudo journalctl -u d2d -f`
- **Documentation**: `/opt/d2d/*.md`

## Security Checklist

- [ ] Changed default API key in `.env`
- [ ] Configured firewall (UFW)
- [ ] Restricted access to trusted IPs only
- [ ] Using SSH keys (not passwords)
- [ ] Configured HTTPS (if needed)
- [ ] Set up regular backups
- [ ] Enabled audit logging

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop d2d
sudo systemctl disable d2d

# Remove service file
sudo rm /etc/systemd/system/d2d.service
sudo systemctl daemon-reload

# Remove D2D directory (CAUTION: This deletes all archived DICOM files!)
sudo rm -rf /opt/d2d

# Remove firewall rule
sudo ufw delete allow 8000/tcp
```

---

**Congratulations!** You now have D2D installed and running.

For detailed usage instructions, see the main README.md file.
