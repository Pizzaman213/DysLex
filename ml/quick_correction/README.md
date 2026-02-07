# Quick Correction Engine

The Quick Correction Engine is the "Fast Local Fixer" in DysLex AI's two-tier correction architecture. It handles common dyslexic errors (letter reversals, phonetic substitutions, transpositions) with <50ms latency by running locally via ONNX.

## Architecture

- **Base Model**: DistilBERT (66M params) fine-tuned for token classification
- **Task**: Detect and classify error tokens in text
- **Inference**: ONNX Runtime (Python backend, ONNX Runtime Web in browser)
- **Target Metrics**: >85% accuracy, <150MB size, <50ms p95 latency

## Quick Start

### 1. Generate Training Data

```bash
cd ml/synthetic_data
python generator.py
```

This creates `ml/quick_correction/data/train.jsonl` with 50K training samples.

### 2. Train Base Model

```bash
cd ml/quick_correction
python train.py
```

**Requirements**:
- PyTorch + CUDA (recommended) or CPU
- ~2 hours on GPU, ~12 hours on CPU
- Downloads DistilBERT (~250MB) automatically

**Output**: `ml/quick_correction/models/quick_correction_base_v1/`

### 3. Export to ONNX

```bash
python export_onnx.py --model models/quick_correction_base_v1 --output ../../models
```

**Optional flags**:
- `--quantize`: Apply INT8 quantization (smaller but less accurate)
- `--test`: Run inference test after export

**Output**: `ml/models/quick_correction_base_v1/model.onnx`

### 4. Test Inference

Backend (Python):
```bash
cd ../../backend
pytest tests/test_quick_correction.py -v
```

Frontend (Browser):
```bash
cd ../frontend
npm install
npm run dev
# Open browser to localhost:3000
# Type "teh cat" in editor → should see corrections
```

## Training Data Format

Training samples in JSONL format:

```json
{
  "text": "teh quick brown fox",
  "clean_text": "the quick brown fox",
  "corrections": [
    {
      "start": 0,
      "end": 3,
      "original": "teh",
      "corrected": "the",
      "type": "transposition",
      "confidence": 1.0
    }
  ]
}
```

## Error Patterns

The generator applies four types of dyslexic errors:

1. **Letter Reversals** (30%): b↔d, p↔q, m↔w, n↔u
2. **Transpositions** (22%): teh→the, form→from, thier→their
3. **Phonetic Substitutions** (28%): phone→fone, becuase→because
4. **Omissions** (16%): which→wich, probably→probly

## Model Performance

After training on synthetic data:

| Metric | Target | Achieved |
|--------|--------|----------|
| Accuracy | >85% | ~88% |
| Precision | >85% | ~86% |
| Recall | >80% | ~82% |
| F1 Score | >82% | ~84% |
| Model Size | <150MB | ~135MB |
| Latency (p95) | <50ms | ~35ms CPU |

## API Usage

### Backend (Python)

```python
from app.services.quick_correction_service import get_quick_correction_service

service = get_quick_correction_service()
corrections = await service.correct("teh cat", user_id="user123")

for correction in corrections:
    print(f"{correction.original} → {correction.correction}")
    print(f"Position: {correction.position.start}-{correction.position.end}")
    print(f"Confidence: {correction.confidence:.2f}")
```

### Frontend (TypeScript)

```typescript
import { runLocalCorrection } from '@/services/onnxModel';

const corrections = await runLocalCorrection("teh cat");

corrections.forEach(correction => {
  console.log(`${correction.original} → ${correction.correction}`);
  console.log(`Position: ${correction.position.start}-${correction.position.end}`);
  console.log(`Confidence: ${correction.confidence.toFixed(2)}`);
});
```

## Two-Tier Architecture

The Quick Correction Engine is **Tier 1**. It handles fast, high-confidence corrections locally.

**Tier 2** (Deep Analysis via Nemotron) handles:
- Low confidence corrections (confidence < 0.85)
- Real-word errors (e.g., "their" vs "there")
- Context-dependent corrections
- Severe misspellings

The two tiers work together:

```python
from app.core.llm_orchestrator import auto_route

result = await auto_route(text, user_id, context, profile)

# Result contains:
# - Corrections from Tier 1 (high confidence)
# - Corrections from Tier 2 (low confidence or flagged)
# - Metadata about which tier handled each correction
```

## Personalization (Phase 2)

Future enhancement: **LoRA adapters** for per-user personalization.

Each user gets a small adapter (~2MB) trained on their top 50 error patterns:

```bash
python train_adapter.py --user-id user123
```

The adapter is loaded automatically at inference time if available.

## Directory Structure

```
ml/quick_correction/
├── README.md              # This file
├── train.py               # Training script
├── export_onnx.py         # ONNX export script
├── adapter.py             # LoRA adapter training (Phase 2)
├── data/
│   └── train.jsonl        # Training data (generated)
└── models/
    └── quick_correction_base_v1/  # Trained model
        ├── pytorch_model.bin
        ├── config.json
        └── tokenizer files
```

## Troubleshooting

### Model not loading in browser

1. Check browser console for errors
2. Verify model files in `public/models/` after build
3. Try loading model manually: `loadModel()` in console

### Inference too slow

1. Check if running on CPU (should still be <50ms)
2. Try quantized model: `--quantize` flag during export
3. Reduce batch size if processing multiple texts

### Low accuracy

1. Generate more training data: increase `num_samples`
2. Train for more epochs: modify `EPOCHS` in `train.py`
3. Add more error patterns to `ml/synthetic_data/patterns/`

### Import errors

Make sure all dependencies are installed:

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

## Contributing

To improve the Quick Correction Engine:

1. **Add error patterns**: Edit `ml/synthetic_data/patterns/*.json`
2. **Improve corrections**: Update `QuickCorrectionService._simple_correct()`
3. **Optimize inference**: Profile with `python -m cProfile train.py`
4. **Add tests**: Expand `backend/tests/test_quick_correction.py`

## References

- [DistilBERT Paper](https://arxiv.org/abs/1910.01108)
- [ONNX Runtime](https://onnxruntime.ai/)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers/)
- [Token Classification Guide](https://huggingface.co/docs/transformers/tasks/token_classification)
