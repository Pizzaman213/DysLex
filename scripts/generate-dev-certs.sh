#!/usr/bin/env bash
#
# Generate local development SSL certificates using mkcert.
# Outputs: certs/dev/localhost+2.pem and certs/dev/localhost+2-key.pem
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERT_DIR="$PROJECT_ROOT/certs/dev"

# Check for mkcert
if ! command -v mkcert &>/dev/null; then
    echo "Error: mkcert is not installed."
    echo ""
    echo "Install it with:"
    echo "  macOS:   brew install mkcert"
    echo "  Linux:   sudo apt install mkcert  (or see https://github.com/FiloSottile/mkcert#installation)"
    echo "  Windows: choco install mkcert"
    exit 1
fi

# Install the local CA (idempotent — safe to run multiple times)
echo "Installing local CA (you may be prompted for your password)..."
mkcert -install

# Generate certificates
mkdir -p "$CERT_DIR"
echo "Generating certificates in $CERT_DIR ..."
mkcert -cert-file "$CERT_DIR/localhost+2.pem" \
       -key-file "$CERT_DIR/localhost+2-key.pem" \
       localhost 127.0.0.1 ::1

echo ""
echo "Done! Certificates created:"
echo "  Cert: $CERT_DIR/localhost+2.pem"
echo "  Key:  $CERT_DIR/localhost+2-key.pem"
echo ""
echo "Start DysLex AI with HTTPS:"
echo "  python3 run.py --https"
