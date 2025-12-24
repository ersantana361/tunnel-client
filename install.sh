#!/bin/bash
# Tunnel Client Installation Script

set -euo pipefail  # Exit on error, undefined vars, pipe failures

echo "Installing Tunnel Client..."

# Check if not running as root
if [ "$EUID" -eq 0 ]; then
    echo "Error: Please do not run as root. We'll use sudo when needed."
    exit 1
fi

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]; }; then
    echo "Error: Python 3.8+ required, found Python $PYTHON_VERSION"
    exit 1
fi
echo "Found Python $PYTHON_VERSION"

# Install Python dependencies
echo "Installing Python dependencies..."
if ! pip3 install -r requirements.txt --break-system-packages 2>/dev/null; then
    # Try without --break-system-packages for older pip versions
    pip3 install -r requirements.txt || {
        echo "Error: Failed to install Python dependencies"
        exit 1
    }
fi

# Install frp client
echo "Installing frp client..."
FRP_VERSION="0.52.3"
FRP_ARCHIVE="frp_${FRP_VERSION}_linux_amd64.tar.gz"
FRP_DIR="frp_${FRP_VERSION}_linux_amd64"

# Download frp
if ! wget -q --show-progress "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/${FRP_ARCHIVE}"; then
    echo "Error: Failed to download frp"
    exit 1
fi

# Extract frp
if ! tar -xzf "$FRP_ARCHIVE"; then
    echo "Error: Failed to extract frp"
    rm -f "$FRP_ARCHIVE"
    exit 1
fi

# Install frpc binary
if ! sudo cp "${FRP_DIR}/frpc" /usr/local/bin/; then
    echo "Error: Failed to install frpc"
    rm -rf "$FRP_ARCHIVE" "$FRP_DIR"
    exit 1
fi
sudo chmod +x /usr/local/bin/frpc

# Clean up
rm -rf "$FRP_ARCHIVE" "$FRP_DIR"

# Verify frpc installation
if ! command -v frpc &> /dev/null; then
    echo "Error: frpc installation verification failed"
    exit 1
fi
echo "frpc installed successfully: $(frpc --version 2>&1 | head -1)"

# Create config directory with proper permissions
echo "Creating config directory..."
sudo mkdir -p /etc/frp
sudo chown "$USER:$USER" /etc/frp
sudo chmod 700 /etc/frp

# Create systemd service
echo "Creating systemd service..."
INSTALL_DIR=$(pwd)
sudo tee /etc/systemd/system/tunnel-client.service > /dev/null <<EOF
[Unit]
Description=Tunnel Client - Web UI for FRP tunnels
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/app.py
Restart=on-failure
RestartSec=10s
StartLimitIntervalSec=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

echo ""
echo "Installation complete!"
echo ""
echo "To start the Tunnel Client:"
echo "  1. Run: python3 app.py"
echo "  2. Open browser: http://127.0.0.1:3000"
echo "  3. Enter your server URL and token"
echo ""
echo "CLI options:"
echo "  python3 app.py --port 3001      # Use different port"
echo "  python3 app.py --host 0.0.0.0   # Listen on all interfaces"
echo ""
echo "Or run as a service:"
echo "  sudo systemctl start tunnel-client"
echo "  sudo systemctl enable tunnel-client  # Auto-start on boot"
echo ""
