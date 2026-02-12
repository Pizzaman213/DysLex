# TODO: Train & Deploy Seq2Seq Quick Correction Model

## Prerequisites

- [ ] Python 3.11+ installed
- [ ] pip dependencies installed (`pip install -r backend/requirements.txt`)
- [ ] ~2GB free disk space for datasets + model files
- [ ] Optional: GPU for faster training (CUDA or Apple Silicon MPS)

## Steps

### 1. Run the full training pipeline (spelling + grammar)

```bash
python3 ml/quick_correction/train_pipeline.py --all --model-type seq2seq --grammar
```

This single command runs all stages:
- Downloads 4 spelling error datasets
- Processes them into seq2seq input/target pairs
- **Generates 30K synthetic grammar errors** (subject-verb, articles, tense, etc.)
- **Generates 5K mixed spelling+grammar errors**
- **Processes GEC datasets** (JFLEG, W&I+LOCNESS if available)
- Combines real + synthetic data (~110K samples)
- Fine-tunes T5-small (8 epochs, LR=2e-4)
- Evaluates on held-out test set (spelling + grammar + no-change)
- Exports to ONNX with INT8 quantization

Expected time: ~2-3 hours on CPU, ~20-30 minutes with GPU.

> **Spelling-only mode** (no grammar): omit `--grammar` flag to train on ~80K spelling samples only.

### 2. Check the eval report

```bash
cat ml/quick_correction/models/quick_correction_seq2seq_v1/eval_report.json
```

- [ ] Spelling exact match accuracy >= 95% (regression check)
- [ ] Grammar exact match accuracy >= 85%
- [ ] No-change accuracy >= 98% (correct text stays unchanged)
- [ ] WER < 0.05
- [ ] P95 latency < 200ms

### 3. Verify ONNX model size

```bash
du -sh ml/models/quick_correction_seq2seq_v1/
```

- [ ] Total size < 200MB

### 4. Start the app and test in browser

```bash
python3 run.py --auto-setup
```

- [ ] Open http://localhost:3000
- [ ] Check browser console for `[ONNX] Quick Correction ready for inference`
- [ ] In Draft mode, type "teh cat sat on teh mat" — spelling corrections appear
- [ ] Type "he go to store yesterday" — grammar corrections appear
- [ ] Type "I have cat at home" — article correction appears
- [ ] Type "She walked and talk to him" — tense correction appears
- [ ] Type correct text — verify no false positives
- [ ] Test novel misspellings NOT in dictionary (e.g. "informashun", "seperate")

### 5. Optional: Download real GEC datasets

For better grammar accuracy, download real grammar error datasets:

```bash
# Place JFLEG data in ml/datasets/raw/jfleg/
# Place W&I+LOCNESS data in ml/datasets/raw/wi_locness/
python3 ml/datasets/process_gec_datasets.py
```

Then retrain with `--grammar` to include this data.

### 6. Done

- [ ] All checks above pass
- [ ] Commit the trained model files
