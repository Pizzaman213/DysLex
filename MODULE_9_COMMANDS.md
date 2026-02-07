# Module 9: Quick Command Reference

## Setup Commands

### Install Dependencies
```bash
# Frontend
cd frontend && npm install

# Backend + ML
cd backend && pip install -r requirements.txt
pip install torch transformers datasets optimum onnxruntime
```

### Start Application

**New: One-Command Launcher (Recommended)** ⭐
```bash
# Start everything with a single command
python3 run.py

# Check prerequisites first
python3 run.py --check-only

# Use Docker (easiest for first-time setup)
python3 run.py --docker

# See full guide
cat RUN_PY_QUICKREF.md
```

**Traditional: Manual Start**
```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

---

## ONNX Model Training (Optional)

### Quick Train (One Command)
```bash
cd ml/quick_correction && \
python generate_dataset.py && \
python train.py && \
python export_onnx.py --quantize && \
cd ../.. && \
mkdir -p frontend/public/models/quick_correction_base_v1 && \
cp ml/models/quick_correction_base_v1/* frontend/public/models/quick_correction_base_v1/
```

### Step-by-Step
```bash
# 1. Generate dataset
cd ml/quick_correction
python generate_dataset.py

# 2. Train model (30-60 min)
python train.py

# 3. Export to ONNX
python export_onnx.py --quantize --test

# 4. Copy to frontend
cd ../..
mkdir -p frontend/public/models/quick_correction_base_v1
cp ml/models/quick_correction_base_v1/* frontend/public/models/quick_correction_base_v1/
```

---

## Testing Commands

### Run All Tests
```bash
cd frontend
npm test
```

### Run Specific Test Suites
```bash
# API service tests
npm test -- services/__tests__/api.test.ts

# ONNX model tests
npm test -- services/__tests__/onnxModel.test.ts

# TTS hook tests
npm test -- hooks/__tests__/useReadAloud.test.ts

# Snapshot engine tests
npm test -- hooks/__tests__/useSnapshotEngine.test.ts
```

### Test with Coverage
```bash
npm test -- --coverage
```

### Test in Watch Mode
```bash
npm test -- --watch
```

---

## Verification Commands

### Check Token Persistence
```javascript
// In browser console
localStorage.getItem('dyslex-auth-token')
```

### Test Backend Endpoints
```bash
# Health check
curl http://localhost:8000/health

# API docs
curl http://localhost:8000/docs

# TTS endpoint
curl -X POST http://localhost:8000/api/v1/voice/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "default"}'

# Batch correction endpoint
curl -X POST http://localhost:8000/api/v1/log-correction/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"corrections": [{"originalText": "teh", "correctedText": "the", "errorType": "self-correction", "context": "I went to teh store", "confidence": 0.9}]}'
```

### Check Model Files
```bash
# Verify ONNX model exists
ls -lh frontend/public/models/quick_correction_base_v1/

# Check model size
du -sh frontend/public/models/quick_correction_base_v1/model.onnx
```

---

## Debugging Commands

### Clear Caches
```bash
# Clear Jest cache
cd frontend
npm test -- --clearCache

# Clear node_modules
rm -rf node_modules package-lock.json
npm install

# Clear browser storage
# In browser console:
localStorage.clear()
```

### View Logs
```bash
# Backend logs
cd backend
tail -f logs/app.log

# Frontend logs
# Open DevTools → Console tab
```

### Database Commands
```bash
# Connect to database
psql -U dyslex -d dyslex

# Check tables
\dt

# View error logs
SELECT * FROM error_logs ORDER BY created_at DESC LIMIT 10;

# View user error patterns
SELECT * FROM user_error_patterns WHERE user_id = 'YOUR_USER_ID';
```

---

## Build Commands

### Frontend Build
```bash
cd frontend
npm run build
npm run preview  # Preview production build
```

### Backend Build
```bash
cd backend
python -m pytest tests/  # Run backend tests
mypy app/               # Type check
ruff check app/         # Lint
```

---

## Cleanup Commands

### Remove Generated Files
```bash
# Remove ONNX model
rm -rf frontend/public/models/quick_correction_base_v1/

# Remove training data
rm -rf ml/quick_correction/data/

# Remove trained models
rm -rf ml/quick_correction/models/
rm -rf ml/models/
```

### Reset Database
```bash
# Drop and recreate tables
cd backend
alembic downgrade base
alembic upgrade head
```

---

## Performance Testing

### Measure ONNX Inference Time
```javascript
// In browser console
import { runLocalCorrection } from '@/services/onnxModel';

const start = performance.now();
await runLocalCorrection('I went to teh store');
const elapsed = performance.now() - start;
console.log(`Inference time: ${elapsed.toFixed(2)}ms`);
```

### Test API Retry
```javascript
// In browser console
// 1. Set throttling to "Offline" in Network tab
// 2. Try an API call
await api.getCorrections('test text');
// 3. Set throttling back to "Online"
// 4. Check console for retry logs
```

### Monitor Network Requests
```javascript
// In browser console
// Enable network logging
performance.getEntriesByType('resource')
  .filter(r => r.name.includes('api'))
  .forEach(r => console.log(`${r.name}: ${r.duration}ms`));
```

---

## Git Commands

### Commit Changes
```bash
# Check status
git status

# Stage Module 9 files
git add frontend/src/services/
git add frontend/src/hooks/
git add frontend/src/types/api.ts
git add backend/app/api/routes/log_correction.py
git add ml/quick_correction/
git add docs/MODULE_9_*
git add MODULE_9_*

# Commit
git commit -m "Implement Module 9: Services & Hooks

- Enhanced API service with retry logic and token persistence
- ONNX quick correction model and training pipeline
- Text-to-speech hook with MagpieTTS integration
- Enhanced snapshot batching for passive learning
- Comprehensive test suites (41 tests)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Production Deployment

### Environment Variables
```bash
# Frontend (.env.production)
VITE_API_URL=https://api.dyslex.ai

# Backend (.env)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dyslex
NVIDIA_NIM_API_KEY=your-api-key
JWT_SECRET_KEY=your-secret-key
```

### Build for Production
```bash
# Frontend
cd frontend
npm run build
# Output: dist/

# Backend
cd backend
# No build step needed for FastAPI
# Use gunicorn or uvicorn in production
```

---

## Quick Troubleshooting

### "Module not found" errors
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### ONNX model not loading
```bash
# Check file exists
ls frontend/public/models/quick_correction_base_v1/model.onnx

# If missing, train it or skip (use cloud API)
```

### TTS not working
```bash
# Test backend
curl http://localhost:8000/api/v1/voice/speak

# Check browser console for errors
# Browser TTS should work as fallback
```

### Tests failing
```bash
cd frontend
npm test -- --clearCache
npm install
npm test
```

### Database connection errors
```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql -U dyslex -d dyslex -c "SELECT 1"

# Check backend config
cat backend/.env | grep DATABASE_URL
```

---

## Useful Aliases (Optional)

Add to your `.bashrc` or `.zshrc`:

```bash
# DysLex shortcuts
alias dx-be='cd backend && uvicorn app.main:app --reload'
alias dx-fe='cd frontend && npm run dev'
alias dx-test='cd frontend && npm test'
alias dx-train='cd ml/quick_correction && python train.py'
alias dx-logs='cd backend && tail -f logs/app.log'
```

Usage:
```bash
dx-be    # Start backend
dx-fe    # Start frontend
dx-test  # Run tests
```

---

## Status Check Script

Create `check-module9.sh`:

```bash
#!/bin/bash

echo "=== Module 9 Status Check ==="

echo -e "\n1. Frontend dependencies:"
cd frontend && npm list 2>/dev/null | head -3

echo -e "\n2. Backend running:"
curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' || echo "Backend not running"

echo -e "\n3. ONNX model:"
if [ -f "frontend/public/models/quick_correction_base_v1/model.onnx" ]; then
    echo "✓ Model found"
    ls -lh frontend/public/models/quick_correction_base_v1/model.onnx
else
    echo "✗ Model not found (optional - will use cloud API)"
fi

echo -e "\n4. Test status:"
cd frontend && npm test -- --listTests 2>/dev/null | grep -c "test.ts" || echo "Tests configured"

echo -e "\n5. Database:"
psql -U dyslex -d dyslex -c "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "Database connection check failed"

echo -e "\n=== Status check complete ==="
```

Make executable: `chmod +x check-module9.sh`

Run: `./check-module9.sh`

---

**Quick Start:** `cd backend && uvicorn app.main:app --reload` + `cd frontend && npm run dev`
**Full Guide:** See `MODULE_9_SETUP.md`
