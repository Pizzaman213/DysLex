# Train Seq2Seq Quick Correction Model

Replaces the BIO-tagging DistilBERT with a T5-small seq2seq model that **directly generates corrected text**, eliminating the dictionary-lookup bottleneck.

## One Command

```bash
python3 ml/quick_correction/train_pipeline.py --all --model-type seq2seq
```

This runs all 6 stages automatically:

1. **Download** — Fetches 4 real-world spelling error datasets (Birkbeck, Aspell, Wikipedia, GitHub Typo Corpus)
2. **Process** — Converts raw word pairs into `{"input_text": "correct: teh cat", "target_text": "the cat"}` sentence pairs
3. **Combine** — Merges real (60%) + synthetic (40%) data into train/val/test splits (~80K samples)
4. **Train** — Fine-tunes T5-small with HuggingFace Seq2SeqTrainer (5 epochs, cosine LR, early stopping)
5. **Evaluate** — Reports exact match accuracy, WER, CER, per-source and per-error-type breakdowns
6. **Export** — Converts to ONNX with INT8 quantization for browser inference

## Individual Stages

```bash
# Just download datasets (shared with BIO pipeline)
python3 ml/quick_correction/train_pipeline.py --download

# Process into seq2seq format
python3 ml/quick_correction/train_pipeline.py --process --model-type seq2seq

# Combine and split
python3 ml/quick_correction/train_pipeline.py --combine --model-type seq2seq

# Train only (uses existing data)
python3 ml/quick_correction/train_pipeline.py --train --model-type seq2seq

# Evaluate only
python3 ml/quick_correction/train_pipeline.py --evaluate --model-type seq2seq

# Export to ONNX only
python3 ml/quick_correction/train_pipeline.py --export --model-type seq2seq
```

## Custom Training Parameters

```bash
python3 ml/quick_correction/train_pipeline.py --all --model-type seq2seq \
  --epochs 10 \
  --batch-size 16 \
  --lr 5e-4 \
  --patience 5 \
  --target-samples 100000
```

| Parameter | Default (seq2seq) | Description |
|-----------|-------------------|-------------|
| `--model-name` | `t5-small` | HuggingFace model ID |
| `--epochs` | `5` | Training epochs |
| `--batch-size` | `32` | Batch size |
| `--lr` | `3e-4` | Learning rate (T5 standard) |
| `--patience` | `3` | Early stopping patience |
| `--target-samples` | `80000` | Total dataset size |

## Output

### Training output
```
ml/quick_correction/models/quick_correction_seq2seq_v1/
├── config.json
├── model.safetensors
├── tokenizer.json
├── tokenizer_config.json
├── spiece.model
├── special_tokens_map.json
├── generation_config.json
└── eval_report.json
```

### ONNX output (served to browser)
```
ml/models/quick_correction_seq2seq_v1/
├── encoder_model.onnx          (~30MB INT8)
├── decoder_model_merged.onnx   (~30MB INT8)
├── config.json
├── generation_config.json
├── tokenizer.json
├── tokenizer_config.json
├── spiece.model
└── special_tokens_map.json
```

## GPU Acceleration

Training on CPU works but is slow (~20min per epoch for 80K samples). For GPU:

```bash
# CUDA (NVIDIA)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# MPS (Apple Silicon) — automatic, no extra install needed
```

The training script auto-detects CUDA and enables fp16 mixed precision.

## How It Works in the Browser

After training and export, the frontend (`frontend/src/services/onnxModel.ts`) uses `@xenova/transformers` to run the T5 model directly in the browser:

```
User types: "teh cat sat on teh mat"
     ↓
Pipeline: "correct: teh cat sat on teh mat"
     ↓
T5 generates: "the cat sat on the mat"
     ↓
Word diff: finds "teh" → "the" (×2)
     ↓
Shows inline corrections
```

Unlike the old BIO model which could only fix words in its 34K-entry dictionary, the seq2seq model can correct **any misspelling** — even ones it has never seen before.

## Old BIO Pipeline (Still Available)

The original DistilBERT pipeline still works:

```bash
python3 ml/quick_correction/train_pipeline.py --all --model-type bio
# or just (bio is the default):
python3 ml/quick_correction/train_pipeline.py --all
```
