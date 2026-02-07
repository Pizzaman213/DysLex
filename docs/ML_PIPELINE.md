# Quick Correction Model -- ML Training Pipeline

## Overview

The Quick Correction Model is the fast, local component of DysLex AI's three-model architecture. It is a DistilBERT-based token classifier that detects spelling errors in real-time directly in the browser using ONNX Runtime Web. The model identifies *where* errors occur in a sentence; correction suggestions are then resolved via a personalized dictionary built from the user's error profile.

The model uses a three-label BIO tagging system:

| Label     | ID | Meaning                        |
|-----------|----|--------------------------------|
| `O`       | 0  | No error (correct token)       |
| `B-ERROR` | 1  | Beginning of an error span     |
| `I-ERROR` | 2  | Inside/continuation of an error span |

The training set comprises approximately 80K samples drawn from four real-world spelling error datasets plus a synthetic data generator. The real-to-synthetic ratio is 60/40, and the test set is held out exclusively from real data for honest evaluation.

---

## Architecture

### Model

- **Base model**: `distilbert-base-uncased` (66M parameters)
- **Task**: Token classification (sequence labeling)
- **Labels**: 3 (`O`, `B-ERROR`, `I-ERROR`)
- **Max sequence length**: 128 tokens
- **Framework**: HuggingFace Transformers + PyTorch for training; ONNX Runtime Web (WASM backend) for inference

### Labeling Scheme

The model uses BIO (Begin, Inside, Outside) labeling at the word level. During tokenization, DistilBERT's WordPiece tokenizer may split a single word into multiple subword tokens. The label alignment logic works as follows:

- Special tokens (`[CLS]`, `[SEP]`, `[PAD]`) receive label `-100` and are ignored during loss computation.
- The first subword token of each word receives the word-level label.
- Continuation subword tokens of an error word receive the same error label; continuation tokens of a correct word receive `-100`.

### Inference Path

The ONNX model runs in the browser via WASM. It detects error positions but does **not** generate correction text itself. Corrections are resolved by looking up the flagged word in a correction dictionary that combines a base dictionary (extracted from training data word pairs) with the user's personalized error profile (from the adaptive learning system).

**Relevant source files**:

| File | Purpose |
|------|---------|
| `frontend/src/services/onnxModel.ts` | Browser-side ONNX inference, tokenization, correction decoding |
| `ml/quick_correction/train.py` | Model fine-tuning script |
| `ml/quick_correction/export_onnx.py` | PyTorch-to-ONNX conversion |

---

## Datasets

The pipeline draws from four real-world spelling error corpora plus a synthetic data generator.

### Real-World Datasets

| Dataset | Approximate Size | Description |
|---------|-----------------|-------------|
| **Birkbeck Corpus** | ~36,000 misspellings | Academic spelling error corpus from Birkbeck, University of London. Lines starting with `$` denote correct words; subsequent lines are their misspellings. |
| **Wikipedia Common Misspellings** | ~4,000+ entries | Crowd-sourced list from Wikipedia's "Lists of common misspellings/For machines" page. Format: `misspelling->correct`. |
| **Aspell Test Data** | ~531 misspellings | Test data from the GNU Aspell spell-checker project. Same format as Birkbeck (correct words prefixed with `$`). |
| **GitHub Typo Corpus** | ~50,000 (filtered) | Real-world typos extracted from GitHub commits. The raw corpus contains 350K+ edits; the pipeline filters to single-word, alphabetic, English typos only. Distributed as compressed JSONL (`jsonl.gz`). |

### Synthetic Data

Approximately 40% of the training set is generated synthetically by the `SyntheticDataGenerator` class. The generator applies four categories of dyslexic error patterns to clean sentences:

| Error Pattern | Probability | Example |
|---------------|-------------|---------|
| Letter reversal | 0.30 | b/d, p/q, m/w, n/u confusion |
| Transposition | 0.22 | Adjacent letter swaps (`teh` -> `the`, `form` -> `from`) |
| Phonetic substitution | 0.28 | Sound-based replacements (`phone` -> `fone`, `laugh` -> `laf`) |
| Omission | 0.16 | Missing letters (`which` -> `wich`, `probably` -> `probly`) |

Error patterns are loaded from JSON configuration files in `ml/synthetic_data/patterns/` (reversals, phonetic, transpositions, omissions). The generator also produces clean (no-error) samples at a ratio of roughly 20% to prevent the model from over-predicting errors.

### Sentence Injection

Raw datasets provide word pairs (misspelling, correct) rather than sentence-level data. The processing stage injects these misspellings into clean sentences from a 2,000-sentence corpus (`ml/datasets/corpus/sentences.txt`):

1. Pick a random clean sentence.
2. Find words in the sentence that match a correct word from the dataset.
3. Replace 1-3 of those words with their misspellings.
4. Generate word-level BIO labels (replaced words get `B-ERROR`, all others get `O`).

---

## Pipeline Stages

The pipeline consists of six sequential stages, orchestrated by `ml/quick_correction/train_pipeline.py`.

### Stage 1: Download

**Script**: `ml/datasets/download_datasets.py`

Downloads the four raw datasets from their public sources using `urllib` (no extra dependencies). Each dataset has primary and mirror URLs for resilience. Files are saved to `ml/datasets/raw/`. If a file already exists locally, the download is skipped.

### Stage 2: Process

**Script**: `ml/datasets/process_datasets.py`

Parses each raw dataset format into `(misspelling, correct)` word pairs using format-specific parsers:

- **Birkbeck / Aspell**: `$correct` header lines followed by misspelling lines.
- **Wikipedia**: Regex matching of `misspelling->correct` patterns (handles both raw wikitext and HTML formats).
- **GitHub Typo Corpus**: JSONL.gz parsing with filters for `is_typo=True`, single-word, alphabetic-only entries.

Each word pair is classified into an error type using edit-distance heuristics:

| Error Type | Detection Rule |
|------------|---------------|
| `transposition` | Same length, same character set, exactly two adjacent positions differ |
| `reversal` | Same length, single character differs, and the pair is in `{b/d, p/q, m/w, n/u}` |
| `omission` | Misspelling is exactly one character shorter; removing one char from correct yields misspelling |
| `insertion` | Misspelling is exactly one character longer; removing one char from misspelling yields correct |
| `phonetic` | A known phonetic substitution pattern (e.g., `ph`/`f`, `tion`/`shun`) transforms misspelling into correct |
| `spelling` | Fallback for everything else |

Word pairs are then injected into clean sentences to produce JSONL files with the schema:

```json
{
  "text": "teh cat sat on the mat",
  "labels": [1, 0, 0, 0, 0, 0],
  "source": "birkbeck",
  "error_type": "transposition"
}
```

Each source also generates clean (all-`O`) samples at 20% of the error sample count to provide negative examples.

Output: one JSONL file per source in `ml/datasets/processed/`.

### Stage 3: Combine

**Script**: `ml/datasets/combine_datasets.py`

Merges the processed real data with freshly generated synthetic data, then splits into train/val/test:

- **Target total**: 80,000 samples (configurable via `--target-samples`).
- **Real/synthetic ratio**: 60% real, 40% synthetic.
- **Test set**: 5% of real data, held out before mixing with synthetic (ensures honest evaluation on real-world errors only).
- **Validation set**: 10% of the combined train+synthetic pool.
- **Random seed**: 42 (for reproducibility).

The synthetic data generator converts its `corrections` format to the same BIO `labels` format used by real data before merging. The combined dataset is shuffled before splitting.

Output: `train.jsonl`, `val.jsonl`, `test.jsonl` in `ml/quick_correction/data/`.

### Stage 4: Train

**Script**: `ml/quick_correction/train.py`

Fine-tunes `distilbert-base-uncased` for token classification using the HuggingFace `Trainer` API.

**Training configuration**:

| Parameter | Default | Notes |
|-----------|---------|-------|
| Epochs | 5 | With early stopping |
| Batch size | 32 | Per-device |
| Learning rate | 2e-5 | |
| LR scheduler | Cosine | With linear warmup |
| Warmup steps | 10% of total steps | |
| Weight decay | 0.01 | |
| Early stopping patience | 3 epochs | Monitored on F1 |
| Mixed precision | fp16 if CUDA available | |
| Best model selection | By F1 score | `load_best_model_at_end=True` |
| Checkpoints kept | 2 | `save_total_limit=2` |

**Data format handling**: The training script auto-detects two input formats. Samples with a `labels` key are used directly. Samples with a `corrections` key (from the synthetic generator) are converted to `labels` format on the fly.

**Evaluation metrics computed during training**:
- Overall accuracy
- Error detection precision, recall, F1 (any non-zero label)
- B-ERROR precision, recall, F1 (class 1 specifically)

The trained model (PyTorch weights, tokenizer, config) is saved to `ml/quick_correction/models/quick_correction_base_v1/`.

### Stage 5: Evaluate

**Script**: `ml/quick_correction/evaluate.py`

Runs the trained model on the held-out test set and produces a detailed evaluation report.

**Report contents**:

1. **Overall metrics**: Accuracy, precision, recall, F1 (both any-error and B-ERROR specific).
2. **Per-source breakdown**: Metrics computed separately for each data source (Birkbeck, Wikipedia, Aspell, GitHub Typo, synthetic) to identify which error domains the model handles best.
3. **Per-error-type breakdown**: Metrics for each error category (reversal, transposition, phonetic, omission, insertion, spelling) to identify which error patterns the model struggles with.
4. **Latency benchmark**: CPU inference latency over 100 samples (5 warmup runs excluded), reporting average, P50, P95, and P99.

Output: `eval_report.json` saved alongside the model in the model directory.

### Stage 6: Export

**Script**: `ml/quick_correction/export_onnx.py`

Converts the trained PyTorch model to ONNX format for browser deployment.

- Uses HuggingFace Optimum (`ORTModelForTokenClassification`) for the conversion.
- Graph optimizations are applied by default.
- Optional INT8 dynamic quantization via `onnxruntime.quantization.quantize_dynamic` reduces model size by approximately 50% (from ~253 MB to ~130 MB) with minimal accuracy loss.
- After export, an automated inference test runs 10 iterations on a sample sentence and reports average and P95 latency.
- Warns if model size exceeds the 150 MB target or if P95 latency exceeds 50ms.

Output: ONNX model, tokenizer, and config saved to `ml/models/quick_correction_base_v1/`.

---

## Usage

### Full Pipeline (All Stages)

```bash
python ml/quick_correction/train_pipeline.py --all
```

### Individual Stages

```bash
# Stage 1: Download raw datasets
python ml/quick_correction/train_pipeline.py --download

# Stage 2: Parse and process into training format
python ml/quick_correction/train_pipeline.py --process

# Stage 3: Combine real + synthetic, create splits
python ml/quick_correction/train_pipeline.py --combine

# Stage 4: Fine-tune DistilBERT
python ml/quick_correction/train_pipeline.py --train

# Stage 5: Evaluate on held-out test set
python ml/quick_correction/train_pipeline.py --evaluate

# Stage 6: Export to ONNX
python ml/quick_correction/train_pipeline.py --export
```

### Multi-Stage Combinations

```bash
# Download and process only (no training)
python ml/quick_correction/train_pipeline.py --download --process

# Evaluate and export (after training separately)
python ml/quick_correction/train_pipeline.py --evaluate --export
```

### Custom Training Parameters

```bash
# Custom epochs, batch size, and learning rate
python ml/quick_correction/train_pipeline.py --train --epochs 10 --batch-size 16 --lr 3e-5

# Custom early stopping patience
python ml/quick_correction/train_pipeline.py --train --patience 5

# Use a different base model
python ml/quick_correction/train_pipeline.py --train --model-name bert-base-uncased

# Custom target sample count
python ml/quick_correction/train_pipeline.py --combine --target-samples 100000

# Export with INT8 quantization
python ml/quick_correction/train_pipeline.py --export --quantize
```

### Standalone Scripts

Each pipeline stage can also be run as a standalone script:

```bash
# Download datasets directly
python ml/datasets/download_datasets.py

# Process datasets directly
python ml/datasets/process_datasets.py

# Combine datasets directly
python ml/datasets/combine_datasets.py

# Train with standalone script (more CLI options)
python ml/quick_correction/train.py --data path/to/train.jsonl --val path/to/val.jsonl --epochs 5

# Export with standalone script
python ml/quick_correction/export_onnx.py --model path/to/model --output path/to/onnx --quantize --test

# Generate synthetic data only
python ml/synthetic_data/generator.py
```

---

## Error Types

The pipeline classifies every misspelling-correct pair into one of six error categories. Classification is performed by `classify_error_type()` in `ml/datasets/process_datasets.py` using edit-distance heuristics.

### reversal

Letter confusion between visually similar characters. Specific pairs checked: `b`/`d`, `p`/`q`, `m`/`w`, `n`/`u`. The words must be the same length with exactly one differing character that belongs to a known reversal pair.

**Examples**: `dag` -> `bag`, `quilt` -> `puilt`

### transposition

Adjacent letter swaps. The misspelling and correct word must have the same length and same character set, with exactly two positions differing and those positions being adjacent.

**Examples**: `teh` -> `the`, `form` -> `from`, `siad` -> `said`

### phonetic

Sound-based substitutions where the writer spells a word the way it sounds rather than using the conventional spelling. Detected by checking if a known phonetic pattern substitution (e.g., `ph`/`f`, `tion`/`shun`, `ight`/`ite`, `ee`/`ea`) transforms the misspelling into the correct word.

**Examples**: `fone` -> `phone`, `enuff` -> `enough`, `nite` -> `night`

### omission

Missing letters. The misspelling is exactly one character shorter than the correct word, and removing a single character from the correct word produces the misspelling.

**Examples**: `wich` -> `which`, `probly` -> `probably`, `beleive` -> `believe`

### insertion

Extra letters. The misspelling is exactly one character longer than the correct word, and removing a single character from the misspelling produces the correct word.

**Examples**: `thhe` -> `the`, `beautifull` -> `beautiful`

### spelling

General fallback category for misspellings that do not match any of the above patterns. Includes multi-character substitutions, complex edits, and other error types.

**Examples**: `accomodate` -> `accommodate`, `definately` -> `definitely`

---

## Performance

### Accuracy Metrics (Held-Out Test Set)

| Metric | Score |
|--------|-------|
| Overall F1 | 0.9919 |
| Precision | High (see eval report) |
| Recall | High (see eval report) |
| B-ERROR F1 | See eval report |

The test set consists exclusively of real-world data (no synthetic samples), ensuring the reported metrics reflect performance on genuine spelling errors.

### Inference Latency

| Runtime | Average | P95 | Notes |
|---------|---------|-----|-------|
| PyTorch (CPU) | 12.5 ms | 14.9 ms | Server-side evaluation |
| ONNX Runtime (CPU) | 2.3 ms | < 5 ms | Python ONNX Runtime |
| ONNX Runtime Web (WASM) | < 100 ms | varies | Browser, depends on device |

The latency target for browser inference is under 50ms per correction on desktop hardware and under 100ms on mobile. The ONNX model with WASM execution provider meets this target on modern devices.

### Model Size

| Format | Size | Notes |
|--------|------|-------|
| PyTorch (full) | ~253 MB | Training checkpoint |
| ONNX (fp32) | ~253 MB | Full precision |
| ONNX (INT8 quantized) | ~130 MB | Dynamic quantization, minimal accuracy loss |

The target model size for browser deployment is under 150 MB. INT8 quantization achieves this with approximately 50% size reduction.

---

## Personalized Dictionary

The ONNX model detects **where** errors occur in text but does not generate correction text itself. Corrections are resolved through a layered dictionary lookup.

### Base Correction Dictionary

A static dictionary of `misspelling -> correction` mappings extracted from the training data word pairs. This ships with the model and provides baseline corrections for the most common errors. The frontend fallback dictionary in `onnxModel.ts` includes entries like:

```
teh -> the
taht -> that
thier -> their
becuase -> because
wich -> which
```

### User Error Profile

The adaptive learning system (see `backend/app/core/error_profile.py` and `backend/app/core/adaptive_loop.py`) builds a per-user error profile by passively observing writing behavior. This profile includes:

- **Error frequency map**: Which specific misspellings the user makes most often.
- **Confusion pairs**: Homophones and similar words the user confuses.
- **Self-correction history**: Errors the user has corrected themselves.

### Merged Lookup

At runtime, the frontend fetches the user's error patterns from the backend API and merges them with the base correction dictionary. When the ONNX model flags a token as an error:

1. Look up the flagged word in the user's personalized error profile.
2. If not found, look up in the base correction dictionary.
3. If still not found, the error is flagged but no automatic correction is offered (the LLM tier handles these).

This design means corrections improve automatically as the user writes, without any model retraining. The ONNX model handles error *detection* (a general skill), while the dictionary handles error *correction* (a personalized skill).

---

## File Structure

```
ml/
├── datasets/
│   ├── __init__.py                 # Package marker
│   ├── download_datasets.py       # Stage 1: Download raw datasets
│   ├── process_datasets.py        # Stage 2: Parse formats, classify errors, inject into sentences
│   ├── combine_datasets.py        # Stage 3: Merge real + synthetic, create train/val/test splits
│   ├── corpus/
│   │   └── sentences.txt          # ~2,000 clean sentences for error injection
│   ├── raw/                       # Downloaded raw dataset files (gitignored)
│   └── processed/                 # Processed JSONL files per source (gitignored)
├── models/
│   └── quick_correction_base_v1/
│       ├── model.onnx             # Exported ONNX model
│       ├── tokenizer.json         # DistilBERT tokenizer
│       ├── config.json            # Model configuration
│       ├── special_tokens_map.json
│       └── vocab.txt              # WordPiece vocabulary
├── quick_correction/
│   ├── train_pipeline.py          # End-to-end pipeline orchestrator
│   ├── train.py                   # Stage 4: Fine-tune DistilBERT
│   ├── evaluate.py                # Stage 5: Per-source/per-type evaluation + latency
│   ├── export_onnx.py             # Stage 6: ONNX export + optional INT8 quantization
│   ├── generate_dataset.py        # Legacy dataset generation script
│   ├── adapter.py                 # Model adapter utilities
│   ├── models/
│   │   └── quick_correction_base_v1/
│   │       ├── pytorch_model.bin  # Trained PyTorch weights
│   │       ├── config.json        # Model config with label mapping
│   │       ├── tokenizer.json     # Saved tokenizer
│   │       ├── eval_report.json   # Evaluation report from Stage 5
│   │       └── logs/              # TensorBoard training logs
│   └── data/
│       ├── train.jsonl            # Training split (~72K samples)
│       ├── val.jsonl              # Validation split (~8K samples)
│       └── test.jsonl             # Test split (real data only, ~4K samples)
├── synthetic_data/
│   ├── generator.py               # Synthetic error pattern generator
│   └── patterns/
│       ├── reversals.json         # b/d, p/q, m/w, n/u patterns
│       ├── phonetic.json          # Sound-based substitution patterns
│       ├── transpositions.json    # Adjacent swap patterns + common examples
│       └── omissions.json         # Letter omission patterns
└── error_classification/
    └── classifier.py              # Error type classification utilities
```

---

## Dependencies

The ML pipeline requires the following Python packages (included in `backend/requirements.txt`):

| Package | Purpose |
|---------|---------|
| `torch` | Model training and inference |
| `transformers` | DistilBERT model, tokenizer, Trainer API |
| `datasets` | HuggingFace dataset utilities |
| `optimum[onnxruntime]` | ONNX export via ORTModelForTokenClassification |
| `onnxruntime` | ONNX inference and INT8 quantization |
| `numpy` | Numerical operations for metrics |

For browser inference, the frontend uses:

| Package | Purpose |
|---------|---------|
| `onnxruntime-web` | ONNX Runtime with WASM backend |
| `@xenova/transformers` | Client-side tokenizer (AutoTokenizer) |

---

## Notes

- The test set is drawn exclusively from real-world data (no synthetic samples) to ensure reported metrics are representative of actual performance.
- The random seed for dataset splitting is fixed at 42 for reproducibility.
- The pipeline gracefully handles partial download failures: if some datasets fail to download, it continues with the available data and adjusts the synthetic data count to reach the target total.
- The synthetic generator produces samples in a `corrections` format (with character offsets); these are automatically converted to the `labels` format (word-level BIO tags) during the combine stage and during training.
- CUDA is auto-detected during training. If available, fp16 mixed precision is enabled for faster training. CPU training is fully supported but slower.
- The model size target of 150 MB is for browser deployment. The training checkpoint is larger (~253 MB) but is not shipped to users.
