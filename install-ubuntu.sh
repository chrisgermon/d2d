#!/bin/bash
################################################################################
# D2D (Documents to DICOM) - Ubuntu Server Installation Script
#
# This script installs D2D on a fresh Ubuntu 22.04/24.04 server
# with all dependencies and configurations
#
# Usage:
#   wget https://raw.githubusercontent.com/chrisgermon/d2d/master/install-ubuntu.sh
#   chmod +x install-ubuntu.sh
#   sudo ./install-ubuntu.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/d2d"
SERVICE_USER="${SUDO_USER:-$USER}"
SERVICE_PORT="8000"
GITHUB_REPO="https://github.com/chrisgermon/d2d.git"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        echo "Please run: sudo ./install-ubuntu.sh"
        exit 1
    fi
}

check_ubuntu() {
    if [ ! -f /etc/os-release ]; then
        print_error "Cannot detect OS version"
        exit 1
    fi

    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        print_warning "This script is designed for Ubuntu"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

################################################################################
# Installation Steps
################################################################################

step_welcome() {
    print_header "D2D Installation"
    echo "This script will install D2D (Documents to DICOM) on your server"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo "Service user: $SERVICE_USER"
    echo "Service port: $SERVICE_PORT"
    echo ""
    read -p "Continue with installation? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        exit 0
    fi
}

step_update_system() {
    print_header "Updating System Packages"
    apt update
    print_success "Package list updated"
}

step_install_dependencies() {
    print_header "Installing Dependencies"

    print_info "Installing Python 3 and development tools..."
    apt install -y python3 python3-venv python3-pip python3-dev build-essential

    print_info "Installing Poppler (PDF processing)..."
    apt install -y poppler-utils

    print_info "Installing ImageMagick (image processing)..."
    apt install -y imagemagick ghostscript libmagickwand-dev

    print_info "Installing Git..."
    apt install -y git

    print_info "Installing network tools..."
    apt install -y netcat-openbsd curl wget

    print_info "Installing firewall (UFW)..."
    apt install -y ufw

    print_success "All dependencies installed"
}

step_configure_imagemagick() {
    print_header "Configuring ImageMagick for PDF Support"

    POLICY_FILE=""
    for f in /etc/ImageMagick-6/policy.xml /etc/ImageMagick/policy.xml; do
        if [ -f "$f" ]; then
            POLICY_FILE="$f"
            break
        fi
    done

    if [ -z "$POLICY_FILE" ]; then
        print_warning "ImageMagick policy file not found, skipping PDF configuration"
    else
        print_info "Backing up ImageMagick policy: ${POLICY_FILE}.backup"
        cp "$POLICY_FILE" "${POLICY_FILE}.backup"

        print_info "Enabling PDF read/write permissions..."
        sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' "$POLICY_FILE"

        print_success "ImageMagick configured for PDF processing"
    fi
}

step_clone_repository() {
    print_header "Installing D2D Application"

    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory $INSTALL_DIR already exists"
        read -p "Remove and reinstall? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            print_error "Installation cancelled"
            exit 1
        fi
    fi

    print_info "Cloning D2D from GitHub..."
    git clone "$GITHUB_REPO" "$INSTALL_DIR"

    print_success "D2D cloned to $INSTALL_DIR"
}

step_setup_python() {
    print_header "Setting Up Python Environment"

    cd "$INSTALL_DIR"

    print_info "Creating Python virtual environment..."
    python3 -m venv venv

    print_info "Activating virtual environment..."
    source venv/bin/activate

    print_info "Upgrading pip..."
    pip install --upgrade pip

    print_info "Installing Python dependencies..."
    pip install -r requirements.txt

    print_success "Python environment configured"
}

step_create_directories() {
    print_header "Creating Working Directories"

    cd "$INSTALL_DIR"

    print_info "Creating directories..."
    mkdir -p uploads dicom_archive temp logs

    print_success "Directories created"
}

step_configure_env() {
    print_header "Configuring Environment"

    cd "$INSTALL_DIR"

    if [ -f ".env" ]; then
        print_warning ".env file already exists"
    else
        print_info "Creating .env file..."
        cat > .env << EOF
# D2D Configuration
HOST=0.0.0.0
PORT=$SERVICE_PORT
ARCHIVE_PATH=./dicom_archive
UPLOAD_PATH=./uploads
MAX_FILE_SIZE=50000000

# API Security (CHANGE THIS!)
D2D_API_KEYS=vrg-d2d-secure-key-$(date +%Y)-change-this-now

# Optional: PACS Configuration
# DEFAULT_PACS_HOST=10.17.1.21
# DEFAULT_PACS_PORT=5000
# DEFAULT_PACS_AE_TITLE=AURVCMOD1
# DEFAULT_CALLING_AE_TITLE=D2D_SCU
EOF
        print_success ".env file created"
        print_warning "IMPORTANT: Edit .env and change the API key!"
    fi
}

step_set_permissions() {
    print_header "Setting Permissions"

    print_info "Setting ownership to $SERVICE_USER..."
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

    print_info "Setting directory permissions..."
    chmod -R 755 "$INSTALL_DIR"
    chmod 700 "$INSTALL_DIR/.env"

    print_success "Permissions configured"
}

step_create_service() {
    print_header "Creating Systemd Service"

    print_info "Creating service file..."
    cat > /etc/systemd/system/d2d.service << EOF
[Unit]
Description=D2D - Documents to DICOM Converter
Documentation=https://github.com/chrisgermon/d2d
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $SERVICE_PORT --proxy-headers --forwarded-allow-ips='*' --timeout-keep-alive 300
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR/uploads $INSTALL_DIR/dicom_archive $INSTALL_DIR/temp $INSTALL_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

    print_info "Reloading systemd..."
    systemctl daemon-reload

    print_success "Systemd service created"
}

step_configure_firewall() {
    print_header "Configuring Firewall"

    print_info "Checking UFW status..."
    if systemctl is-active --quiet ufw; then
        print_info "UFW is active, adding rules..."
        ufw allow $SERVICE_PORT/tcp
        print_success "Firewall rule added for port $SERVICE_PORT"
    else
        print_warning "UFW is not active"
        read -p "Enable firewall and allow port $SERVICE_PORT? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ufw --force enable
            ufw allow $SERVICE_PORT/tcp
            ufw allow ssh
            print_success "Firewall enabled and configured"
        fi
    fi
}

step_test_installation() {
    print_header "Testing Installation"

    print_info "Testing Python dependencies..."
    cd "$INSTALL_DIR"
    source venv/bin/activate
    python3 -c "import fastapi, uvicorn, pydicom, pynetdicom; print('All modules loaded successfully')"
    print_success "Python dependencies OK"

    print_info "Testing PDF conversion..."
    if command -v pdftoppm &> /dev/null; then
        print_success "Poppler installed OK"
    else
        print_warning "pdftoppm not found - PDF conversion may not work"
    fi

    print_info "Testing ImageMagick..."
    if command -v convert &> /dev/null; then
        print_success "ImageMagick installed OK"
    else
        print_warning "ImageMagick convert not found"
    fi
}

step_start_service() {
    print_header "Starting D2D Service"

    print_info "Enabling service to start on boot..."
    systemctl enable d2d

    print_info "Starting D2D service..."
    systemctl start d2d

    sleep 3

    if systemctl is-active --quiet d2d; then
        print_success "D2D service is running"
    else
        print_error "D2D service failed to start"
        print_info "Check logs with: sudo journalctl -u d2d -n 50"
        return 1
    fi
}

step_final_instructions() {
    print_header "Installation Complete!"

    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')

    echo -e "${GREEN}D2D has been successfully installed!${NC}\n"

    echo "📍 Installation Directory: $INSTALL_DIR"
    echo "🌐 Web Interface: http://$SERVER_IP:$SERVICE_PORT"
    echo "👤 Service User: $SERVICE_USER"
    echo ""

    echo "📋 Service Management Commands:"
    echo "  sudo systemctl status d2d     # Check status"
    echo "  sudo systemctl start d2d      # Start service"
    echo "  sudo systemctl stop d2d       # Stop service"
    echo "  sudo systemctl restart d2d    # Restart service"
    echo "  sudo journalctl -u d2d -f     # View live logs"
    echo ""

    echo "⚙️  Configuration:"
    echo "  Edit config: nano $INSTALL_DIR/.env"
    echo "  After changes: sudo systemctl restart d2d"
    echo ""

    echo "🔒 Security:"
    print_warning "IMPORTANT: Change the API key in $INSTALL_DIR/.env"
    echo "  Edit the D2D_API_KEYS value to a secure random string"
    echo ""

    echo "🔧 Testing PACS Connectivity:"
    echo "  nc -zv YOUR_PACS_IP YOUR_PACS_PORT"
    echo "  Example: nc -zv 10.17.1.21 5000"
    echo ""

    echo "📚 Documentation:"
    echo "  README: $INSTALL_DIR/README.md"
    echo "  On-Prem Guide: $INSTALL_DIR/ONPREM-DEPLOYMENT.md"
    echo "  GitHub: https://github.com/chrisgermon/d2d"
    echo ""

    echo "🔗 Connect from Claude Code:"
    echo "  See: $INSTALL_DIR/CLAUDE-CODE-SETUP.md"
    echo ""

    if systemctl is-active --quiet d2d; then
        echo -e "${GREEN}✓ D2D is running and ready to use!${NC}"
        echo -e "Access it at: ${BLUE}http://$SERVER_IP:$SERVICE_PORT${NC}"
    else
        echo -e "${RED}⚠ Service is not running. Check logs:${NC}"
        echo "  sudo journalctl -u d2d -n 50"
    fi
}

################################################################################
# Main Installation Flow
################################################################################

main() {
    check_root
    check_ubuntu
    step_welcome
    step_update_system
    step_install_dependencies
    step_configure_imagemagick
    step_clone_repository
    step_setup_python
    step_create_directories
    step_configure_env
    step_set_permissions
    step_create_service
    step_configure_firewall
    step_test_installation
    step_start_service
    step_final_instructions
}

# Run installation
main "$@"

exit 0
