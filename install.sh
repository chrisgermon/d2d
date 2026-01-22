#!/bin/bash
# D2D Installation Script
# Run with: sudo ./install.sh

set -e

echo "=== D2D Installation ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo ./install.sh"
    exit 1
fi

# Installation directory
INSTALL_DIR="/opt/d2d"

# Create installation directory
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p $INSTALL_DIR

# Copy files
echo "Copying files..."
cp -r /home/claudeagent/d2d/* $INSTALL_DIR/

# Set ownership to crowdit
echo "Setting ownership to crowdit..."
chown -R crowdit:crowdit $INSTALL_DIR

# Create working directories
echo "Creating working directories..."
cd $INSTALL_DIR
mkdir -p uploads dicom_archive temp
chown crowdit:crowdit uploads dicom_archive temp

# Create .env file
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    chown crowdit:crowdit .env
fi

# Open firewall
echo "Opening firewall port 8000..."
ufw allow 8000/tcp

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/d2d.service <<'EOF'
[Unit]
Description=Documents to DICOM (D2D)
After=network.target

[Service]
Type=simple
User=crowdit
Group=crowdit
WorkingDirectory=/opt/d2d
Environment="PATH=/opt/d2d/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/d2d/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "Next steps:"
echo "1. As crowdit user, run: cd /opt/d2d && python3 -m venv venv"
echo "2. Activate venv: source /opt/d2d/venv/bin/activate"
echo "3. Install packages: pip install -r /opt/d2d/requirements.txt"
echo "4. Start service: sudo systemctl start d2d"
echo "5. Enable on boot: sudo systemctl enable d2d"
echo ""
echo "Or run manually: cd /opt/d2d && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Access at: http://10.60.60.172:8000"
echo ""
