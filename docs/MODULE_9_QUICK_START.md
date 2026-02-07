# Module 9: Quick Start Guide

This guide walks you through getting Module 9 (Services & Hooks) up and running.

---

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Running PostgreSQL database
- Backend server running on port 8000

---

## Step 1: Install Dependencies

### Frontend
```bash
cd frontend
npm install
```

### Backend (ML Training)
```bash
cd backend
pip install -r requirements.txt

# Additional ML dependencies
pip install torch transformers datasets optimum onnxruntime
```

---

## Step 2: Train ONNX Quick Correction Model (Optional)

**Note:** This step is optional. The frontend will fall back to the cloud API if the local model is not available.

### Generate Training Dataset
```bash
cd ml/quick_correction
python generate_dataset.py
```

**Expected output:**
```
Generating dyslexic error dataset...
✓ Generated 8000 training examples
✓ Generated 2000 validation examples
✓ Saved to ml/quick_correction/data

Sample corrupted sentences:
  I went to [teh] store
  She [sed] it was [importent]
  ...
```

### Train the Model
```bash
python train.py
```

**Expected duration:** 30-60 minutes on GPU, 2-3 hours on CPU

**Expected output:**
```
Starting Quick Correction Model training...
Loading distilbert-base-uncased...
Preparing datasets (7200 train, 800 eval)...
Starting training...

Epoch 1/3: 100%|████████| 225/225 [15:23<00:00]
Eval results: {'accuracy': 0.863, 'f1': 0.821}

...

Training complete!
Model size: 135.4 MB
```

### Export to ONNX
```bash
python export_onnx.py --quantize --test
```

**Expected output:**
```
Exporting model to ONNX format...
Saving ONNX model...
Applying INT8 quantization...
  Original: 267.3 MB
  Quantized: 83.1 MB
  Reduction: 68.9%

Testing ONNX model from ml/models/quick_correction_base_v1...
Running inference on: 'teh cat sat on teh mat'
Inference times (10 runs):
  Average: 42.31 ms
  P95: 48.72 ms
✓ Latency within target (<50ms)
```

### Copy to Frontend
```bash
# From project root
mkdir -p frontend/public/models/quick_correction_base_v1
cp ml/models/quick_correction_base_v1/* frontend/public/models/quick_correction_base_v1/
```

---

## Step 3: Start the Application

### Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

Visit: http://localhost:3000

---

## Step 4: Verify Functionality

### 1. Token Persistence

1. Open DevTools → Application → Local Storage
2. Login to the app
3. Check for `dyslex-auth-token` key
4. Refresh the page
5. ✅ Verify you're still logged in

### 2. API Retry Logic

1. Open DevTools → Network tab
2. Set throttling to "Offline"
3. Try to make an API call (e.g., get corrections)
4. Set throttling back to "Online"
5. ✅ Verify the request retries and succeeds

### 3. ONNX Quick Correction

**If you trained the model:**
1. Type "I went to teh store" in the editor
2. Wait for quick correction
3. ✅ Verify "teh" is underlined/corrected to "the"

**If you skipped training:**
1. Corrections will use cloud API instead
2. ✅ This is expected behavior

### 4. Text-to-Speech

1. Type some text in the editor
2. Click the "Read Aloud" button
3. ✅ Verify audio plays

**Troubleshooting:**
- If MagpieTTS fails, browser TTS should play instead
- Check browser console for TTS errors
- Verify backend `/api/v1/voice/speak` endpoint is available

### 5. Snapshot Batching

1. Open DevTools → Network tab
2. Type "I recieve mail"
3. Wait 3 seconds
4. Correct it to "I receive mail"
5. Wait 10 seconds
6. ✅ Check for POST to `/api/v1/log-correction/batch`

**What to look for:**
```json
{
  "corrections": [
    {
      "originalText": "recieve",
      "correctedText": "receive",
      "errorType": "self-correction",
      "context": "I recieve mail",
      "confidence": 0.89
    }
  ]
}
```

---

## Step 5: Run Tests

### Frontend Tests
```bash
cd frontend

# Run all tests
npm test

# Run specific test suites
npm test -- services/__tests__/api.test.ts
npm test -- services/__tests__/onnxModel.test.ts
npm test -- hooks/__tests__/useReadAloud.test.ts
npm test -- hooks/__tests__/useSnapshotEngine.test.ts

# Run with coverage
npm test -- --coverage
```

**Expected output:**
```
PASS  src/services/__tests__/api.test.ts
  API Service
    Token Persistence
      ✓ saves token to localStorage (12 ms)
      ✓ retrieves token from localStorage (3 ms)
      ✓ clears token when set to null (2 ms)
      ✓ survives page refresh (3 ms)
    Retry Logic
      ✓ retries on 500 error (45 ms)
      ✓ does not retry on 400 error (8 ms)
    ...

Test Suites: 4 passed, 4 total
Tests:       41 passed, 41 total
```

---

## Common Issues

### Issue: ONNX Model Not Loading

**Symptom:** Console error: `Failed to load ONNX model`

**Solution:**
1. Check model file exists:
   ```bash
   ls frontend/public/models/quick_correction_base_v1/model.onnx
   ```
2. If missing, train and export the model (Step 2)
3. Or, skip local model and use cloud API instead

---

### Issue: TTS Not Working

**Symptom:** No audio plays when clicking "Read Aloud"

**Solution:**
1. Check backend is running on port 8000
2. Test MagpieTTS endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/v1/voice/speak \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello world", "voice": "default"}'
   ```
3. If MagpieTTS unavailable, browser TTS should play instead
4. Check browser console for errors

---

### Issue: Batch Endpoint Not Called

**Symptom:** No POST to `/api/v1/log-correction/batch` after self-corrections

**Solution:**
1. Verify you corrected yourself (not just typed new text)
2. Wait at least 10 seconds for batch flush
3. Check browser console for errors
4. Verify backend endpoint exists:
   ```bash
   curl http://localhost:8000/docs
   # Look for POST /api/v1/log-correction/batch
   ```

---

### Issue: Tests Failing

**Symptom:** `npm test` shows failures

**Solution:**
1. Ensure all dependencies installed: `npm install`
2. Check Node version: `node --version` (should be 18+)
3. Clear Jest cache: `npm test -- --clearCache`
4. Run tests in watch mode: `npm test -- --watch`

---

## Performance Benchmarks

After completing setup, verify these benchmarks:

| Component | Metric | Target | How to Test |
|-----------|--------|--------|-------------|
| Token Persistence | Survives refresh | 100% | Refresh page, check still logged in |
| API Retry | Success rate | >95% | Simulate 500 error, verify retries |
| ONNX Load | Initial load | <2s | Watch network tab on page load |
| ONNX Inference | Per call | <100ms | Type "teh" and measure correction time |
| TTS Start | Time to audio | <500ms | Click read aloud, measure delay |
| Snapshot Batch | Batch size | 5 corrections | Correct 5 typos, check network tab |

---

## Next Steps

Once Module 9 is working:

1. **Module 10**: Integration & End-to-End Testing
2. **Module 11**: Deployment & Production Optimization
3. **Module 12**: User Onboarding & Documentation

---

## Getting Help

If you encounter issues:

1. Check browser console for errors
2. Check backend logs: `tail -f backend/logs/app.log`
3. Review network tab for failed requests
4. Consult the full implementation plan in `docs/MODULE_9_IMPLEMENTATION_SUMMARY.md`

---

## Summary Checklist

- [ ] Dependencies installed (frontend + backend)
- [ ] ONNX model trained and exported (optional)
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Token persistence verified
- [ ] API retry logic tested
- [ ] ONNX corrections working (or cloud fallback)
- [ ] TTS playing audio
- [ ] Snapshot batching logging corrections
- [ ] All tests passing

**Congratulations!** Module 9 is now fully operational.
