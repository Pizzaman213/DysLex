# Quickstart Guide

Get DysLex AI running on your machine.

---

## Prerequisites

| Requirement | Minimum Version | Check Command |
|-------------|----------------|---------------|
| Python | 3.11+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| npm | 9+ | `npm --version` |
| PostgreSQL | 15+ | `psql --version` |
| Redis | 7+ | `redis-server --version` |

**Optional:**
- **NVIDIA NIM API key** — required for cloud-based Nemotron corrections, MagpieTTS, and faster-whisper STT
- **Docker** — for containerized deployment
- **GPU** — for ML model training (Google Colab free tier works)

---

## One-Command Setup (Recommended)

```bash
python3 run.py --auto-setup
```

This single command:
1. Starts PostgreSQL if not running
2. Starts Redis if not running
3. Creates the backend virtual environment
4. Installs Python dependencies
5. Kills processes on conflicting ports (8000, 3000)
6. Starts the backend (port 8000) and frontend (port 3000)

After the first run, you can use the shorter form:

```bash
python3 run.py
```

---

## Manual Setup

### Database

```bash
# Start PostgreSQL and Redis (macOS/Homebrew)
brew services start postgresql@15
brew services start redis

# Create the database
createdb dyslex
psql dyslex < database/schema/init.sql
psql dyslex < database/seeds/error_types.sql
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # starts on port 3000
```

---

## Docker Setup

```bash
# Full stack
docker compose -f docker/docker-compose.yml up

# Development mode (with hot reload)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up
```

Services running in Docker: Frontend (3000), Backend (8000), PostgreSQL (5432), Redis (6379).

---

## Environment Variables

Create a `.env` file in the project root or export these variables:

### Required

```bash
NVIDIA_NIM_API_KEY=your-api-key      # For Nemotron, MagpieTTS, faster-whisper
DATABASE_URL=postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex
```

### Optional

```bash
VITE_API_URL=http://localhost:8000   # Backend URL for frontend
JWT_SECRET_KEY=change-me             # For authentication
REDIS_URL=redis://localhost:6379/0   # Redis connection string
SNAPSHOT_TTL_HOURS=24                # Snapshot expiry for privacy
```

---

## Verify It Works

After starting services, check these:

| Check | How |
|-------|-----|
| Frontend | Open http://localhost:3000 |
| Backend (Swagger) | Open http://localhost:8000/docs |
| Backend health | `curl -s http://localhost:8000/health` |
| PostgreSQL | `pg_isready` |
| Redis | `redis-cli ping` |

---

## Training the ML Model (Optional)

The Quick Correction ONNX model is optional — the system falls back to cloud API if unavailable.

```bash
# Full pipeline: download datasets, process, combine, train, evaluate, export
python ml/quick_correction/train_pipeline.py --all

# Or run individual stages
python ml/quick_correction/train_pipeline.py --download   # Download raw datasets
python ml/quick_correction/train_pipeline.py --process    # Parse into training format
python ml/quick_correction/train_pipeline.py --combine    # Merge real + synthetic data
python ml/quick_correction/train_pipeline.py --train      # Fine-tune DistilBERT
python ml/quick_correction/train_pipeline.py --evaluate   # Evaluate on test set
python ml/quick_correction/train_pipeline.py --export     # Export to ONNX

# Export with INT8 quantization (smaller model)
python ml/quick_correction/train_pipeline.py --export --quantize

# Copy to frontend for browser inference
mkdir -p frontend/public/models/quick_correction_base_v1
cp ml/models/quick_correction_base_v1/* frontend/public/models/quick_correction_base_v1/
```

**Training on Google Colab (free GPU):**
1. Upload `train.py` and generated data to Colab
2. `!pip install transformers torch datasets accelerate`
3. `!python train.py`
4. Download and extract model locally

---

## `run.py` Command Reference

```bash
python3 run.py --auto-setup            # First-time setup (handles everything)
python3 run.py                          # Start (after initial setup)
python3 run.py --docker                 # Start with Docker Compose
python3 run.py --backend-only           # Start only backend
python3 run.py --frontend-only          # Start only frontend
python3 run.py --backend-port 8080 --frontend-port 3001  # Custom ports
python3 run.py --check-only             # Check prerequisites without starting
python3 run.py --https                  # Start with HTTPS (requires certs)
python3 run.py --https --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem
```

---

## SSL / HTTPS Setup

### Local Development (mkcert)

```bash
# Install mkcert
brew install mkcert        # macOS
sudo apt install mkcert    # Linux
choco install mkcert       # Windows

# Generate locally-trusted certificates
bash scripts/generate-dev-certs.sh

# Start with HTTPS
python3 run.py --https
```

Open `https://localhost:3000` — you should see a green lock icon.

### Production (Docker + Let's Encrypt)

```bash
# Set DOMAIN in docker/.env
cp docker/.env.example docker/.env

# Bootstrap certificates
docker compose -f docker/docker-compose.yml -f docker/docker-compose.ssl.yml \
  run --rm certbot certonly --webroot -w /var/www/certbot \
  -d your-domain.com --email you@example.com --agree-tos --no-eff-email

# Start with SSL
docker compose -f docker/docker-compose.yml -f docker/docker-compose.ssl.yml up -d
```

Nginx handles TLS termination, ACME challenges, and HTTP→HTTPS redirect. The certbot container auto-renews certificates every 12 hours.

---

## Production Considerations

- **Frontend:** Build with `npm run build`, serve via Nginx or CDN, enable gzip
- **Backend:** Use Gunicorn with Uvicorn workers, enable connection pooling
- **Database:** Enable PgBouncer, regular backups, read replicas for scaling
- **Security:** HTTPS everywhere, CORS configuration, rate limiting, input validation

---

## Troubleshooting

### Port Conflicts

```bash
# Auto-setup kills conflicting processes automatically
python3 run.py --auto-setup

# Or manually
lsof -ti :8000 | xargs kill
lsof -ti :3000 | xargs kill
```

### PostgreSQL or Redis Not Starting

```bash
# macOS (Homebrew)
brew services start postgresql@15
brew services start redis

# Verify
pg_isready
redis-cli ping
```

### Services Already Running

```bash
pkill -f "run.py"
python3 run.py --auto-setup
```

### SSL Certificates Not Found

```bash
bash scripts/generate-dev-certs.sh
```

If the browser shows "not secure" with mkcert, run `mkcert -install` and restart your browser.

### CORS Errors Over HTTPS

The backend includes both `http://` and `https://` origins for localhost. For custom ports, add them to `CORS_ORIGINS` in your `.env`.
