# D2D Installation & Claude Code Integration - Summary

This document summarizes the complete installation package created for D2D.

## What's Been Created

### 1. **install-ubuntu.sh** - Complete Ubuntu Installation Script
A comprehensive, production-ready installation script that:
- ✓ Checks system requirements (Ubuntu 22.04/24.04)
- ✓ Installs all dependencies (Python, Poppler, ImageMagick, Git)
- ✓ Configures ImageMagick for PDF processing
- ✓ Clones D2D from GitHub
- ✓ Sets up Python virtual environment
- ✓ Creates systemd service for automatic startup
- ✓ Configures firewall (UFW)
- ✓ Sets proper permissions
- ✓ Tests installation
- ✓ Provides clear post-installation instructions

**Usage**:
```bash
curl -fsSL https://raw.githubusercontent.com/chrisgermon/d2d/master/install-ubuntu.sh | sudo bash
```

Or:
```bash
wget https://raw.githubusercontent.com/chrisgermon/d2d/master/install-ubuntu.sh
chmod +x install-ubuntu.sh
sudo ./install-ubuntu.sh
```

### 2. **MCP Server** - Claude Code Integration
A complete Model Context Protocol server (`mcp-server/`) that allows Claude Code to interact with D2D seamlessly.

**Features**:
- Direct integration with Claude Code
- 8 tools for D2D operations:
  - d2d_health_check
  - d2d_upload_file
  - d2d_list_destinations
  - d2d_add_destination
  - d2d_verify_destination
  - d2d_send_to_pacs
  - d2d_list_archives
  - d2d_convert_document

**Setup**:
```bash
cd /opt/d2d/mcp-server
npm install
```

Add to `~/.config/claude/mcp.json`:
```json
{
  "mcpServers": {
    "d2d": {
      "command": "node",
      "args": ["/opt/d2d/mcp-server/index.js"],
      "env": {
        "D2D_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

### 3. **d2d-cli.sh** - Command Line Interface
A user-friendly CLI wrapper for D2D API operations.

**Commands**:
- `status` - Check server health
- `upload` - Upload and convert files
- `destinations` - List DICOM destinations
- `add-destination` - Add new PACS server
- `verify` - Test PACS connection (C-ECHO)
- `send` - Send DICOM to PACS
- `archives` - List archived files

**Examples**:
```bash
./d2d-cli.sh status
./d2d-cli.sh upload document.pdf "Smith^John" "12345"
./d2d-cli.sh destinations
./d2d-cli.sh send patient_123.dcm "Intelerad PACS"
```

### 4. **CLAUDE-CODE-SETUP.md** - Integration Guide
Comprehensive guide covering 4 methods to connect Claude Code to D2D:
1. SSH Tunnel (easiest)
2. Direct Network Access
3. MCP Server (best integration)
4. API Wrapper Script

Includes:
- Setup instructions for each method
- Complete API endpoint documentation
- Security best practices
- Troubleshooting guide
- Usage examples

### 5. **QUICK-INSTALL.md** - Quick Start Guide
Step-by-step quick start guide covering:
- One-line installation
- Post-installation configuration
- Claude Code connection setup
- Testing procedures
- Common commands
- Troubleshooting

## Installation Flow

```
┌─────────────────────────────────────────┐
│  Run install-ubuntu.sh                  │
│  (Installs D2D on Ubuntu server)        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  D2D Server Running                     │
│  - Web UI: http://SERVER_IP:8000       │
│  - Systemd service: d2d.service         │
│  - Location: /opt/d2d                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Connect from Claude Code               │
│                                          │
│  Option A: SSH Tunnel                   │
│  ssh -L 8000:localhost:8000 user@server │
│                                          │
│  Option B: MCP Server                   │
│  Configure ~/.config/claude/mcp.json    │
│                                          │
│  Option C: CLI Script                   │
│  Use d2d-cli.sh from local machine      │
└─────────────────────────────────────────┘
```

## File Structure

```
d2d/
├── install-ubuntu.sh           # NEW: Ubuntu installation script
├── d2d-cli.sh                  # NEW: CLI wrapper for API
├── CLAUDE-CODE-SETUP.md        # NEW: Claude Code integration guide
├── QUICK-INSTALL.md            # NEW: Quick start guide
├── INSTALLATION-SUMMARY.md     # NEW: This file
│
├── mcp-server/                 # NEW: MCP server for Claude Code
│   ├── package.json
│   ├── index.js
│   └── README.md
│
├── app/                        # Existing D2D application
│   ├── main.py
│   ├── dicom_converter.py
│   ├── dicom_sender.py
│   └── ...
│
├── static/                     # Existing web interface
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── requirements.txt            # Existing Python deps
├── README.md                   # Existing main readme
├── ONPREM-DEPLOYMENT.md        # Existing deployment guide
└── ...                         # Other existing files
```

## Quick Start Commands

### Install D2D
```bash
curl -fsSL https://raw.githubusercontent.com/chrisgermon/d2d/master/install-ubuntu.sh | sudo bash
```

### Connect via SSH Tunnel
```bash
ssh -L 8000:localhost:8000 user@d2d-server-ip
```

### Install MCP Server
```bash
cd /opt/d2d/mcp-server
npm install
```

### Use CLI
```bash
./d2d-cli.sh status
./d2d-cli.sh upload file.pdf "Doe^John" "12345"
```

## Claude Code Integration Methods

### Method 1: SSH Tunnel (Recommended for Getting Started)
**Pros**: Simple, secure, no additional setup
**Cons**: Requires active SSH session

```bash
ssh -L 8000:localhost:8000 user@d2d-server
# Then use http://localhost:8000 from Claude Code
```

### Method 2: MCP Server (Recommended for Best Experience)
**Pros**: Native Claude Code integration, natural language commands
**Cons**: Requires Node.js, initial configuration

```json
{
  "mcpServers": {
    "d2d": {
      "command": "node",
      "args": ["/opt/d2d/mcp-server/index.js"],
      "env": {"D2D_API_URL": "http://localhost:8000"}
    }
  }
}
```

### Method 3: CLI Script (Recommended for Scripting)
**Pros**: Simple bash scripting, easy to automate
**Cons**: Less interactive than MCP

```bash
export D2D_URL=http://localhost:8000
./d2d-cli.sh upload document.pdf "Smith^John" "12345"
```

### Method 4: Direct API Calls
**Pros**: Maximum flexibility
**Cons**: More verbose

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@document.pdf" \
  -F "patient_name=Doe^John" \
  -F "patient_id=12345"
```

## Security Features

The installation includes:
- ✓ Systemd service hardening (NoNewPrivileges, ProtectSystem, etc.)
- ✓ Firewall configuration (UFW)
- ✓ API key authentication support
- ✓ Secure directory permissions
- ✓ SSH key authentication support

**Important**: Remember to change the default API key in `/opt/d2d/.env` after installation!

## Testing Checklist

After installation, test:
- [ ] Web interface accessible: `curl http://SERVER_IP:8000/api/health`
- [ ] Service is running: `sudo systemctl status d2d`
- [ ] PACS connectivity: `nc -zv PACS_IP PACS_PORT`
- [ ] PDF conversion: Upload a test PDF through web UI
- [ ] DICOM send: Send test file to PACS
- [ ] Claude Code connection: Test SSH tunnel or MCP server
- [ ] CLI tool: Run `./d2d-cli.sh status`

## Common Post-Installation Tasks

### 1. Change API Key
```bash
sudo nano /opt/d2d/.env
# Change D2D_API_KEYS value
sudo systemctl restart d2d
```

### 2. Add PACS Destination
```bash
./d2d-cli.sh add-destination "My PACS" "PACSAE" "10.0.0.10" "104" "D2D_SCU"
```

### 3. Test PACS Connection
```bash
./d2d-cli.sh verify "PACSAE" "10.0.0.10" "104" "D2D_SCU"
```

### 4. Set Up Auto-Start
```bash
sudo systemctl enable d2d
```

### 5. Configure Firewall
```bash
sudo ufw allow 8000/tcp
sudo ufw enable
```

## Troubleshooting Resources

1. **Service Logs**: `sudo journalctl -u d2d -f`
2. **Installation Logs**: Check terminal output from install script
3. **API Health**: `curl http://localhost:8000/api/health`
4. **Network Test**: `nc -zv PACS_IP PACS_PORT`
5. **Documentation**: See CLAUDE-CODE-SETUP.md for detailed troubleshooting

## What's Next?

1. **Configure PACS**: Add your PACS destinations
2. **Test Workflow**: Upload a test document and send to PACS
3. **Set Up Claude Code**: Choose integration method and configure
4. **Enable HTTPS**: Follow ONPREM-DEPLOYMENT.md for Nginx setup
5. **Configure Backups**: Set up regular backups of `/opt/d2d/dicom_archive/`
6. **Monitor**: Set up log monitoring and alerts

## Support & Documentation

- **Main README**: `/opt/d2d/README.md`
- **On-Prem Guide**: `/opt/d2d/ONPREM-DEPLOYMENT.md`
- **Claude Code Setup**: `/opt/d2d/CLAUDE-CODE-SETUP.md`
- **Quick Install**: `/opt/d2d/QUICK-INSTALL.md`
- **MCP Server**: `/opt/d2d/mcp-server/README.md`
- **GitHub**: https://github.com/chrisgermon/d2d
- **Issues**: https://github.com/chrisgermon/d2d/issues

## License

MIT License - See LICENSE file for details

---

**Created**: 2026-01-25
**For**: D2D (Documents to DICOM) Project
**Purpose**: Complete Ubuntu installation and Claude Code integration
