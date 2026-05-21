#!/bin/bash
#
# deploy/generate-selfsigned-cert.sh
# Generate a self-signed certificate for Vigil HTTPS collector
# Usage: ./generate-selfsigned-cert.sh [domain-or-ip]

set -e

DOMAIN=${1:-localhost}
DAYS=365
CERT_FILE="fullchain.pem"
KEY_FILE="privkey.pem"

echo "🔐 Generating self-signed certificate for: $DOMAIN (valid $DAYS days)"

echo "[1/2] Creating private key and certificate..."
openssl req -x509 -nodes -days $DAYS -newkey rsa:2048 \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -subj "/CN=$DOMAIN" \
  -addext "subjectAltName=DNS:$DOMAIN,IP:127.0.0.1,IP:::1" 2>/dev/null || \
openssl req -x509 -nodes -days $DAYS -newkey rsa:2048 \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -subj "/CN=$DOMAIN"

echo "[2/2] Setting permissions..."
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo ""
echo "✅ Done! Self-signed certificate generated:"
echo "   📄 Certificate: $CERT_FILE"
echo "   🔑 Private Key: $KEY_FILE"
echo ""
echo "📌 How to use in your Python bot:"
echo '   from receiver import start_vigil_server'
echo "   start_vigil_server('0.0.0.0', 9901, storage, engine, alert_callback,"
echo "                      token='your-token',"
echo "                      certfile='$CERT_FILE',"
echo "                      keyfile='$KEY_FILE')"
echo ""
echo "⚠️  Note: This is self-signed. For production use Let's Encrypt or real CA certs."
echo "   Browsers/agents will show warning unless you add the cert to trust store."
