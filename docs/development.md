# Development Guide

Internal implementation details for DysLex AI's features, ML pipeline, and services layer. For high-level architecture, see [how-it-works.md](how-it-works.md).

---

## ML Training Pipeline

The Quick Correction Model is a DistilBERT-based token classifier (66M params) that detects spelling errors in-browser using ONNX Runtime Web with BIO tagging (`O`, `B-ERROR`, `I-ERROR`).

### Pipeline Stages

```bash
python ml/quick_correction/train_pipeline.py --all    # Run all 6 stages
```

| Stage | Script | What It Does |
|-------|--------|-------------|
| 1. Download | `ml/datasets/download_datasets.py` | Downloads 4 raw datasets (Birkbeck, Wikipedia, Aspell, GitHub Typo Corpus) |
| 2. Process | `ml/datasets/process_datasets.py` | Parses formats, classifies error types, injects misspellings into sentences |
| 3. Combine | `ml/datasets/combine_datasets.py` | Merges real (60%) + synthetic (40%) data, creates train/val/test splits (~80K samples) |
| 4. Train | `ml/quick_correction/train.py` | Fine-tunes DistilBERT (5 epochs, cosine LR, early stopping on F1) |
| 5. Evaluate | `ml/quick_correction/evaluate.py` | Per-source and per-error-type metrics + latency benchmark |
| 6. Export | `ml/quick_correction/export_onnx.py` | ONNX conversion with optional INT8 quantization (~253MB → ~130MB) |

### Training Configuration

| Parameter | Default |
|-----------|---------|
| Base model | `distilbert-base-uncased` |
| Epochs | 5 (early stopping patience: 3) |
| Batch size | 32 |
| Learning rate | 2e-5 (cosine scheduler) |
| Max sequence length | 128 tokens |
| Mixed precision | fp16 if CUDA available |

### Error Type Classification

| Type | Detection Rule | Example |
|------|---------------|---------|
| Reversal | Same length, single b/d/p/q/m/w/n/u swap | dag → bag |
| Transposition | Same length, same chars, 2 adjacent positions differ | teh → the |
| Phonetic | Known phonetic pattern (ph/f, tion/shun, ight/ite) | fone → phone |
| Omission | 1 char shorter, removing 1 char from correct = misspelling | wich → which |
| Insertion | 1 char longer, removing 1 char from misspelling = correct | thhe → the |
| Spelling | Fallback | definately → definitely |

### Synthetic Data Generation

`ml/synthetic_data/generator.py` applies 4 error patterns to clean text:
- Letter reversals (30%), transpositions (22%), phonetic substitutions (28%), omissions (16%)
- Patterns loaded from JSON configs in `ml/synthetic_data/patterns/`
- ~20% clean (no-error) samples to prevent over-prediction

### Personalized Dictionary

The ONNX model detects **where** errors are but doesn't generate corrections. Corrections resolved via:
1. User's personal error profile (from adaptive learning)
2. Base correction dictionary (from training data)
3. If neither matches, flagged for Tier 2 LLM

### Performance

| Metric | Score |
|--------|-------|
| Overall F1 | 0.9919 |
| ONNX latency (CPU) | 2.3ms avg |
| ONNX model size (INT8) | ~130 MB |
| Browser target | <50ms desktop, <100ms mobile |

### File Structure

```
ml/
├── datasets/
│   ├── download_datasets.py       # Stage 1
│   ├── process_datasets.py        # Stage 2
│   ├── combine_datasets.py        # Stage 3
│   └── corpus/sentences.txt       # Clean sentences for error injection
├── quick_correction/
│   ├── train_pipeline.py          # End-to-end orchestrator
│   ├── train.py                   # Stage 4
│   ├── evaluate.py                # Stage 5
│   ├── export_onnx.py             # Stage 6
│   └── test_dyslexic.py           # Dyslexic writing test suite
├── synthetic_data/
│   ├── generator.py               # Synthetic error generator
│   └── patterns/*.json            # Error pattern configs
└── models/quick_correction_base_v1/
    ├── model.onnx                 # Exported ONNX model
    └── tokenizer.json             # DistilBERT tokenizer
```

---

## Adaptive Learning Loop

The passive learning system that makes DysLex AI adaptive. Learns from user behavior without explicit feedback.

### Backend Snapshot Processing

**File:** `backend/app/core/adaptive_loop.py`

- Full LCS (Longest Common Subsequence) word-level diff algorithm
- Change detection: substitutions, insertions, deletions
- Similarity calculation using Levenshtein distance
- Self-correction filtering (0.3 < similarity < 0.95)
- Error type classification (letter_reversal, homophone, phonetic, omission, spelling)
- Automatic error profile updates

### Redis Snapshot Storage

**File:** `backend/app/services/redis_client.py`

- Rolling window of last 50 snapshots per user
- Automatic 24-hour TTL for privacy
- Memory-bounded (256MB with LRU eviction)
- Raw text never stored in PostgreSQL — only derived error patterns persist

### Scheduled Jobs (APScheduler)

**File:** `backend/app/services/scheduler.py`

| Schedule | Job | Purpose |
|----------|-----|---------|
| Daily 2:00 AM | No-change word detection | Auto-add to personal dictionary |
| Daily 2:30 AM | Model retraining check | Retrain Quick Correction if threshold met |
| Monday 3:00 AM | Improvement patterns | Mark improving error types |
| Monday 3:30 AM | Progress snapshots | Weekly aggregate stats |

Manual trigger: `POST /api/v1/learn/trigger-retrain`

### End-to-End Flow

```
User types "I saw teh cat" → Snapshot captured (5s interval)
→ User corrects to "I saw the cat" → Pause detected (3s idle)
→ POST /api/v1/snapshots → Previous snapshot from Redis
→ LCS diff → "teh"→"the" detected (similarity: 0.67)
→ Classified as letter_reversal → error_profile_service.log_error()
→ Database updated (error_logs, user_error_patterns)
→ Next LLM prompt includes updated pattern
```

---

## Progress Dashboard

### Backend

**File:** `backend/app/db/repositories/progress_repo.py`

7 query functions operating on the existing `error_logs` table (no new tables needed):
- `get_error_frequency_by_week()` — weekly error counts
- `get_error_breakdown_by_type()` — errors by type per week
- `get_top_errors()` — most frequent error pairs
- `get_mastered_words()` — words with 3+ self-corrections
- `get_writing_streak()` — current and longest streaks
- `get_total_stats()` — lifetime metrics
- `get_improvement_by_error_type()` — trends with sparkline data

Single endpoint: `GET /api/v1/progress/dashboard?weeks=12`

### Frontend

4 new components using Recharts and react-sparklines:
- **WritingStreaksStats** — 4 stat cards (streak, longest, words, sessions)
- **WordsMastered** — celebratory badge grid
- **ImprovementTrends** — sparklines with trend badges (improving/stable/needs attention)
- **ErrorFrequencyCharts** — line chart, stacked bar chart, horizontal bar chart

All metrics frame progress positively. Never shows raw error counts.

---

## Emotional Check-In System

Passive frustration detection that offers gentle support during Draft Mode.

### Behavioral Signals

| Signal | Threshold | Weight |
|--------|-----------|--------|
| Rapid deletion | >20 chars in 3 seconds | 0.4 |
| Long pause | >30 seconds mid-sentence | 0.2 |
| Short bursts | <5 words, 3+ times in a row | 0.3 |
| Cursor thrashing | 5+ jumps >50 chars in 10 seconds | 0.3 |

Signals decay exponentially over 2 minutes. Check-in triggered at score >= 0.6 with 10-minute cooldown and 2-minute spacing from AI Coach nudges.

### Key Files
- `frontend/src/hooks/useFrustrationDetector.ts` — Detection and scoring (~350 lines)
- `frontend/src/components/Editor/CheckInPrompt.tsx` — Banner UI
- `frontend/src/utils/checkInMessages.ts` — Empathetic message database

---

## Services & Hooks Layer

Client-side logic connecting React UI to FastAPI backend.

### Enhanced API Service (`frontend/src/services/api.ts`)

- **Token persistence** — survives page refresh via localStorage
- **Retry logic** — exponential backoff (1s, 2s, 4s) on 5xx errors, max 3 retries
- **Request cancellation** — AbortController prevents redundant in-flight requests
- **User-friendly errors** — maps HTTP status codes to plain English messages
- **Batch correction endpoint** — reduces API calls by 5x for passive learning

### ONNX Quick Correction Hook (`frontend/src/hooks/useQuickCorrection.ts`)

React hook wrapping browser-side ONNX inference with loading states, error handling, and graceful fallback to cloud API.

### Text-to-Speech Hook (`frontend/src/hooks/useReadAloud.ts`)

Two-tier TTS: MagpieTTS (primary, high quality) with browser SpeechSynthesis fallback. Supports play/pause/resume/stop, speed control (0.5x-2.0x), respects `voiceEnabled` setting.

### Enhanced Snapshot Batching

- Signal categorization: self-correction (similarity >60%) vs. rewrite
- Batch size: 5 corrections before API call, periodic 10s flush
- Silent failures — API errors never interrupt the writer
- Corrections logged to `POST /api/v1/log-correction/batch`

---

## Export & Sharing

### Export Formats

**File:** `frontend/src/services/exportService.ts`

- **DOCX** — via `html-to-docx`
- **PDF** — via `html2pdf.js` (client-side, multi-page)
- **HTML** — standalone with embedded styles
- **Plain Text** — with optional metadata

### Dialog Component (`frontend/src/components/Shared/Dialog.tsx`)

Reusable accessible modal: portal rendering, focus trap, Escape to close, backdrop click, ARIA attributes, body scroll prevention.

### Export Menu (`frontend/src/components/Editor/ExportMenu.tsx`)

Dropdown with full keyboard navigation (Arrow keys, Enter, Escape), loading states, toast notifications.

---

## Dependencies

### ML Pipeline (Python)
`torch`, `transformers`, `datasets`, `optimum[onnxruntime]`, `onnxruntime`, `numpy`

### Backend (Python)
`fastapi`, `sqlalchemy[asyncio]`, `pydantic`, `redis>=5.0.0`, `apscheduler>=3.10.0`

### Frontend (npm)
`onnxruntime-web`, `@xenova/transformers`, `recharts`, `react-sparklines`, `html-to-docx`, `html2pdf.js`, `file-saver`
