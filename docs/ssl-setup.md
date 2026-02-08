# SSL / HTTPS Setup

DysLex AI supports HTTPS for both local development and production deployments. HTTPS is opt-in — existing HTTP workflows continue to work unchanged.

## Local Development (mkcert)

### 1. Install mkcert

```bash
# macOS
brew install mkcert

# Linux (Debian/Ubuntu)
sudo apt install mkcert

# Windows
choco install mkcert
```

### 2. Generate Certificates

```bash
bash scripts/generate-dev-certs.sh
```

This creates locally-trusted certificates in `certs/dev/`:
- `certs/dev/localhost+2.pem` (certificate)
- `certs/dev/localhost+2-key.pem` (private key)

The certificates cover `localhost`, `127.0.0.1`, and `::1`.

### 3. Start with HTTPS

```bash
python3 run.py --https
```

Both the backend (uvicorn) and frontend (Vite) will serve over HTTPS. Open `https://localhost:3000` in your browser — you should see a green lock icon.

### Custom Certificate Paths

```bash
python3 run.py --https --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem
```

---

## Production (Docker + Let's Encrypt)

### 1. Configure Environment

Copy and edit the environment file:

```bash
cp docker/.env.example docker/.env
```

Set these variables in `docker/.env`:
```bash
DOMAIN=your-domain.com
```

### 2. Bootstrap Certificates

On the first run, obtain certificates from Let's Encrypt:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.ssl.yml \
  run --rm certbot certonly --webroot -w /var/www/certbot \
  -d your-domain.com --email you@example.com --agree-tos --no-eff-email
```

### 3. Start with SSL

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.ssl.yml up -d
```

Nginx will:
- Serve ACME challenges on port 80 for cert renewal
- Redirect all other HTTP traffic to HTTPS
- Terminate TLS on port 443 with strong cipher configuration
- Proxy API requests to the backend over the internal Docker network

The `certbot` service automatically renews certificates every 12 hours.

### 4. Certificate Renewal

Certificates are renewed automatically by the certbot container. To force a manual renewal:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.ssl.yml \
  run --rm certbot renew
```

Then reload nginx to pick up new certificates:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.ssl.yml \
  exec dyslex-web nginx -s reload
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_ENABLE_HTTPS` | (unset) | Set to `true` to enable Vite HTTPS dev server |
| `VITE_API_URL` | (protocol-aware) | Backend API URL; set automatically by `--https` flag |
| `DOMAIN` | `localhost` | Production domain for Let's Encrypt and nginx |
| `SSL_CERT_PATH` | — | Custom certificate path (production) |
| `SSL_KEY_PATH` | — | Custom private key path (production) |

---

## Troubleshooting

### "SSL certificates not found"

Run the generation script:
```bash
bash scripts/generate-dev-certs.sh
```

### Browser shows "not secure" with mkcert

Make sure `mkcert -install` ran successfully. This installs a local CA into your system trust store. You may need to restart your browser after installation.

### CORS errors over HTTPS

The backend CORS configuration includes both `http://` and `https://` origins for `localhost:3000` and `localhost:5173`. If you use a custom port, add it to `CORS_ORIGINS` in your `.env`:

```bash
CORS_ORIGINS=["https://localhost:3000","https://localhost:5173","https://localhost:YOUR_PORT"]
```

### Certificate renewal fails in Docker

Ensure port 80 is accessible from the internet — Let's Encrypt needs to reach `/.well-known/acme-challenge/` on your server. Check firewall rules and DNS configuration.

### Mixed content warnings

If the frontend loads over HTTPS but API calls go to HTTP, the browser will block them. Ensure `VITE_API_URL` uses `https://` or let the default protocol detection handle it (the frontend auto-detects `window.location.protocol`).
