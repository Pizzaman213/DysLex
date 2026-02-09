#!/usr/bin/env bash
#
# Generate local development SSL certificates using mkcert.
# Ensures the CA is trusted in the OS trust store and Firefox NSS store.
# Works on macOS and Linux. (Windows users: run mkcert -install manually.)
# Outputs: certs/dev/localhost+2.pem and certs/dev/localhost+2-key.pem
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERT_DIR="$PROJECT_ROOT/certs/dev"
OS="$(uname)"

# ── 1. Check for mkcert ─────────────────────────────────────────────────────
if ! command -v mkcert &>/dev/null; then
    echo "Error: mkcert is not installed."
    echo ""
    echo "Install it with:"
    echo "  macOS:   brew install mkcert"
    echo "  Ubuntu/Debian: sudo apt install mkcert"
    echo "  Fedora:  sudo dnf install mkcert"
    echo "  Arch:    sudo pacman -S mkcert"
    echo "  Other:   https://github.com/FiloSottile/mkcert#installation"
    exit 1
fi

CA_ROOT="$(mkcert -CAROOT)"
CA_PEM="$CA_ROOT/rootCA.pem"

# ── 2. Install NSS tools for Firefox ────────────────────────────────────────
if ! command -v certutil &>/dev/null; then
    echo "Installing nss (needed for Firefox certificate support)..."
    if [[ "$OS" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            brew install nss
        else
            echo "Warning: Homebrew not found. Install nss manually for Firefox support:"
            echo "  brew install nss"
        fi
    elif [[ "$OS" == "Linux" ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y libnss3-tools
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y nss-tools
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm nss
        else
            echo "Warning: Could not detect package manager. Install nss/certutil manually for Firefox support."
        fi
    fi
fi

# ── 3. Run mkcert -install ──────────────────────────────────────────────────
echo "Installing local CA (you may be prompted for your password)..."
if ! mkcert -install; then
    echo ""
    echo "Warning: mkcert -install failed. You can try manually:"
    echo "  1. Run: mkcert -install"
    echo "  2. If prompted, enter your password"
    echo "  3. Re-run this script"
    echo ""
    echo "Continuing with certificate generation..."
fi

# ── 4. Verify CA trust in OS trust store ────────────────────────────────────
if [[ -f "$CA_PEM" ]]; then
    if [[ "$OS" == "Darwin" ]]; then
        echo "Verifying CA trust in macOS Keychain..."
        if security verify-cert -c "$CA_PEM" &>/dev/null; then
            echo "  CA is trusted in macOS Keychain."
        else
            echo "  CA is NOT trusted. Adding to System Keychain (requires sudo)..."
            if sudo security add-trusted-cert -d -r trustRoot \
                -k /Library/Keychains/System.keychain \
                "$CA_PEM"; then
                if security verify-cert -c "$CA_PEM" &>/dev/null; then
                    echo "  CA is now trusted in macOS Keychain."
                else
                    echo ""
                    echo "  Warning: CA still not trusted after adding to Keychain."
                    echo "  Manual fix: Open Keychain Access > System > find 'mkcert' cert"
                    echo "  > Get Info > Trust > set 'Always Trust'"
                fi
            else
                echo ""
                echo "  Warning: Could not add CA to System Keychain."
                echo "  Manual fix:"
                echo "    sudo security add-trusted-cert -d -r trustRoot \\"
                echo "        -k /Library/Keychains/System.keychain \\"
                echo "        \"$CA_PEM\""
            fi
        fi
    elif [[ "$OS" == "Linux" ]]; then
        echo "Verifying CA trust in Linux trust store..."
        # Check if the CA is already in the system trust store
        TRUST_INSTALLED=false
        if command -v trust &>/dev/null; then
            if trust list 2>/dev/null | grep -q "mkcert"; then
                TRUST_INSTALLED=true
            fi
        fi

        if [[ "$TRUST_INSTALLED" == true ]]; then
            echo "  CA is trusted in system trust store."
        else
            echo "  CA may not be in system trust store. Attempting to add..."
            if command -v update-ca-certificates &>/dev/null; then
                # Debian/Ubuntu
                sudo cp "$CA_PEM" /usr/local/share/ca-certificates/mkcert-rootCA.crt
                sudo update-ca-certificates
                echo "  CA added to system trust store."
            elif command -v update-ca-trust &>/dev/null; then
                # Fedora/RHEL/CentOS
                sudo cp "$CA_PEM" /etc/pki/ca-trust/source/anchors/mkcert-rootCA.pem
                sudo update-ca-trust
                echo "  CA added to system trust store."
            else
                echo "  Warning: Could not detect trust store manager."
                echo "  mkcert -install should have handled this. If browsers still"
                echo "  show warnings, copy $CA_PEM to your system CA directory manually."
            fi
        fi
    fi
fi

# ── 5. Check Firefox NSS database ──────────────────────────────────────────
if command -v certutil &>/dev/null; then
    # Determine Firefox profiles directory by OS
    if [[ "$OS" == "Darwin" ]]; then
        FF_PROFILES_DIR="$HOME/Library/Application Support/Firefox/Profiles"
    elif [[ "$OS" == "Linux" ]]; then
        FF_PROFILES_DIR="$HOME/.mozilla/firefox"
    else
        FF_PROFILES_DIR=""
    fi

    if [[ -n "$FF_PROFILES_DIR" && -d "$FF_PROFILES_DIR" ]]; then
        FOUND_NSS=false
        MISSING_NSS=false

        for profile_dir in "$FF_PROFILES_DIR"/*; do
            [[ -d "$profile_dir" ]] || continue
            if [[ -f "$profile_dir/cert9.db" ]]; then
                if certutil -L -d "sql:$profile_dir" 2>/dev/null | grep -q "mkcert"; then
                    FOUND_NSS=true
                else
                    MISSING_NSS=true
                fi
            fi
        done

        if [[ "$MISSING_NSS" == true ]]; then
            echo "CA missing from some Firefox profiles. Re-running mkcert -install..."
            mkcert -install 2>/dev/null || true
        elif [[ "$FOUND_NSS" == true ]]; then
            echo "  CA is present in Firefox NSS store."
        fi
    fi
fi

# ── 6. Generate certificates ────────────────────────────────────────────────
mkdir -p "$CERT_DIR"
echo "Generating certificates in $CERT_DIR ..."
mkcert -cert-file "$CERT_DIR/localhost+2.pem" \
       -key-file "$CERT_DIR/localhost+2-key.pem" \
       localhost 127.0.0.1 ::1

# ── 7. Summary ──────────────────────────────────────────────────────────────
echo ""
echo "Done! Certificates created:"
echo "  Cert: $CERT_DIR/localhost+2.pem"
echo "  Key:  $CERT_DIR/localhost+2-key.pem"
echo ""
echo "Start DysLex AI with HTTPS:"
echo "  python3 run.py --https"
echo ""
echo "Browser notes:"
echo "  Chrome/Safari/Edge: Restart the browser if you see a certificate warning."
echo "  Firefox: If you still see a warning after restarting:"
echo "    1. Go to Settings > Privacy & Security > Certificates > View Certificates"
echo "    2. Import: $CA_PEM"
echo "    3. Check 'Trust this CA to identify websites' and click OK"
