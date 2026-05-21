#!/bin/bash
set -e
if [ $# -lt 2 ]; then
    echo "Usage: bash install.sh <arch> <hostname> [server_url]"
    echo "  arch: amd64 | arm64"
    echo "  hostname: unique name for this server"
    echo "  server_url: default http://your-server:9901"
    exit 1
fi
ARCH=$1
HOSTNAME=$2
SERVER_URL=${3:-"http://your-server:9901"}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$SCRIPT_DIR/vigil-agent-linux-$ARCH"

# Check binary exists before copying
if [ ! -f "$BINARY" ]; then
    echo "ERROR: Binary not found: $BINARY"
    echo "Make sure you have the correct architecture: amd64 or arm64"
    echo "And the compiled binary exists in the deploy directory."
    exit 1
fi

cp "$BINARY" /usr/local/bin/vigil-agent
chmod +x /usr/local/bin/vigil-agent
mkdir -p /etc/vigil
cat > /etc/vigil/config.json << CONFIGEOF
{
    "server_url": "$SERVER_URL",
    "interval": 30,
    "hostname": "$HOSTNAME"
}
CONFIGEOF
cp "$SCRIPT_DIR/vigil-agent.service" /etc/systemd/system/vigil-agent.service
systemctl daemon-reload
systemctl enable vigil-agent
systemctl start vigil-agent
echo "Vigil Agent installed successfully!"
