# TODO: Train & Deploy Seq2Seq Quick Correction Model

## Prerequisites

- [ ] Python 3.11+ installed
- [ ] pip dependencies installed (`pip install -r backend/requirements.txt`)
- [ ] ~2GB free disk space for datasets + model files
- [ ] Optional: GPU for faster training (CUDA or Apple Silicon MPS)

## Steps

### 1. Run the full training pipeline

```bash
python3 ml/quick_correction/train_pipeline.py --all --model-type seq2seq
```

This single command runs all 6 stages:
- Downloads 4 spelling error datasets
- Processes them into seq2seq input/target pairs
- Combines real + synthetic data (~80K samples)
- Fine-tunes T5-small (5 epochs)
- Evaluates on held-out test set
- Exports to ONNX with INT8 quantization

Expected time: ~1-2 hours on CPU, ~15-20 minutes with GPU.

### 2. Check the eval report

```bash
cat ml/quick_correction/models/quick_correction_seq2seq_v1/eval_report.json
```

- [ ] Exact match accuracy > 95%
- [ ] WER < 0.05
- [ ] P95 latency < 200ms

### 3. Verify ONNX model size

```bash
du -sh ml/models/quick_correction_seq2seq_v1/
```

- [ ] Total size < 100MB (INT8 quantized)

### 4. Start the app and test in browser

```bash
python3 run.py --auto-setup
```

- [ ] Open http://localhost:3000
- [ ] Check browser console for `[ONNX] Quick Correction ready for inference`
- [ ] In Draft mode, type "teh cat sat on teh mat" — corrections should appear inline
- [ ] Test novel misspellings NOT in dictionary (e.g. "informashun", "seperate") — these should now get corrections

### 5. Done

- [ ] All checks above pass
- [ ] Commit the trained model files
