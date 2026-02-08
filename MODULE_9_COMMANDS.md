# Module 9 Command Reference

Quick-reference cheat sheet. No prose — just commands.

---

## Service Management (`run.py`)

```bash
# Start everything with auto-setup (first time)
python3 run.py --auto-setup

# Start (after initial setup)
python3 run.py

# Start with Docker Compose
python3 run.py --docker

# Start only backend
python3 run.py --backend-only

# Start only frontend
python3 run.py --frontend-only

# Custom ports
python3 run.py --backend-port 8080 --frontend-port 3001

# Check prerequisites without starting
python3 run.py --check-only
```

---

## MCP Tools (Claude Code)

Use these by asking Claude Code in natural language, or reference the tool names directly.

### dyslex_start

Start services.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | string | `"dev"` | `"dev"`, `"docker"`, `"backend"`, `"frontend"` |
| `auto_setup` | boolean | `false` | Auto-handle prerequisites |
| `backend_port` | integer | `8000` | Backend port |
| `frontend_port` | integer | `3000` | Frontend port |

```python
dyslex_start(auto_setup=True)
dyslex_start(mode="docker")
dyslex_start(mode="backend", backend_port=8080)
```

### dyslex_stop

Stop all services. No parameters.

```python
dyslex_stop()
```

### dyslex_status

Check service health. No parameters. Returns process status, port status, and URLs.

```python
dyslex_status()
```

### dyslex_logs

View recent logs.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lines` | integer | `50` | Number of lines |
| `service` | string | `"all"` | `"all"`, `"backend"`, `"frontend"`, `"system"` |

```python
dyslex_logs(lines=100, service="backend")
```

### dyslex_restart

Restart services.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `auto_setup` | boolean | `false` | Use auto-setup on restart |

```python
dyslex_restart(auto_setup=True)
```

### dyslex_check

Run prerequisite checks without starting. No parameters.

```python
dyslex_check()
```

### dyslex_screenshot

Take a screenshot of the frontend.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | `"http://localhost:3000"` | URL to capture |
| `width` | integer | `1280` | Viewport width (px) |
| `height` | integer | `900` | Viewport height (px) |
| `wait` | integer | `3000` | Wait time before capture (ms) |
| `full_page` | boolean | `false` | Capture full scrollable page |

```python
dyslex_screenshot()
dyslex_screenshot(url="http://localhost:3000/draft", width=1440)
dyslex_screenshot(full_page=True, wait=5000)
```

---

## Hooks

All hooks live in `.claude/hooks/`.

### Make All Hooks Executable

```bash
chmod +x .claude/hooks/*.sh
```

### Enable/Disable Auto-Start

```bash
# Enable
sed -i '' 's/TRIGGER="manual"/TRIGGER="on-enter"/' .claude/hooks/auto-start.sh

# Disable
sed -i '' 's/TRIGGER="on-enter"/TRIGGER="manual"/' .claude/hooks/auto-start.sh
```

### Hook Summary

| Hook | File | Runs |
|------|------|------|
| Format Code | `format-code.sh` | Prettier (TS/JS), Ruff format (Python) |
| Lint Check | `lint-check.sh` | ESLint (TS/JS), Ruff check (Python) |
| Run Tests | `run-tests.sh` | Jest (frontend), pytest (backend) |
| Type Check | `typecheck.sh` | tsc --noEmit (TS), mypy (Python) |
| Auto-Start | `auto-start.sh` | Starts services on project open |

---

## ML Pipeline

### Generate Training Dataset

```bash
cd ml/quick_correction
python generate_dataset.py
```

### Train Quick Correction Model

```bash
cd ml/quick_correction
python train.py
```

### Export to ONNX

```bash
cd ml/quick_correction
python export_onnx.py --quantize --test
```

### Copy Model to Frontend

```bash
mkdir -p frontend/public/models/quick_correction_base_v1
cp ml/models/quick_correction_base_v1/* frontend/public/models/quick_correction_base_v1/
```

---

## Testing

### Frontend

```bash
cd frontend

# All tests
npm test

# Specific suites
npm test -- services/__tests__/api.test.ts
npm test -- services/__tests__/onnxModel.test.ts
npm test -- hooks/__tests__/useReadAloud.test.ts
npm test -- hooks/__tests__/useSnapshotEngine.test.ts

# With coverage
npm test -- --coverage

# Type check
npm run type-check

# Lint
npm run lint
```

### Backend

```bash
cd backend

# All tests
pytest tests/ -v

# Specific test
pytest tests/ -k <test_name>

# Type check
mypy app/ --ignore-missing-imports

# Lint
ruff check app/

# Format
ruff format app/
```

---

## Troubleshooting One-Liners

```bash
# Kill process on port 8000
lsof -ti :8000 | xargs kill

# Kill process on port 3000
lsof -ti :3000 | xargs kill

# Check if backend is healthy
curl -s http://localhost:8000/health

# Check if frontend is running
curl -s http://localhost:3000 > /dev/null && echo "OK" || echo "DOWN"

# Check PostgreSQL
pg_isready

# Check Redis
redis-cli ping

# Start PostgreSQL (macOS/Homebrew)
brew services start postgresql@15

# Start Redis (macOS/Homebrew)
brew services start redis

# View backend logs
tail -f backend/logs/app.log

# Clear Jest cache
cd frontend && npm test -- --clearCache

# Kill all DysLex AI processes
pkill -f "run.py"
```

---

## Related Docs

- [Module 9 Setup Guide](MODULE_9_SETUP.md) — Full setup walkthrough
- [Module 9 Implementation Summary](docs/MODULE_9_IMPLEMENTATION_SUMMARY.md) — Technical details
- [MCP Server Docs](.claude/README.md) — MCP server architecture and advanced usage
