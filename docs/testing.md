# Testing

DysLex AI has a full testing subsystem covering the ML models, the correction pipeline, the adaptive learning loop, the frontend UI components, and the backend API services.

---

## ML Model Tests

Test the ONNX and seq2seq models on realistic dyslexic writing patterns — letter reversals, transpositions, phonetic substitutions, omissions, homophones, insertions, and severe mixed errors.

```bash
# Run the dyslexic writing test suite (39 hand-crafted samples, 8 error categories)
python ml/quick_correction/test_dyslexic.py

# With sample-level details showing every input/output
python ml/quick_correction/test_dyslexic.py --verbose

# Test only the seq2seq correction model
python ml/quick_correction/test_dyslexic.py --seq2seq-only

# Test only the ONNX error detection model
python ml/quick_correction/test_dyslexic.py --onnx-only
```

---

## ML Benchmarks

```bash
# Full benchmark: latency, throughput, accuracy, memory (ONNX + PyTorch)
python ml/quick_correction/benchmark.py

# ONNX only, 200 runs
python ml/quick_correction/benchmark.py --onnx-only --runs 200

# Seq2seq evaluation on 2,400-sample test corpus
python ml/quick_correction/evaluate_seq2seq.py
```

---

## Frontend Tests

34 test files covering UI components, services, hooks, and stores.

```bash
cd frontend

# Run all tests
npm test

# Run a specific test file or pattern
npm test -- --testPathPattern=grammarRules
npm test -- --testPathPattern=contextRules
npm test -- --testPathPattern=correctionService

# Type checking and linting
npm run type-check
npm run lint
```

### What's Covered

- **Correction pipeline** — ONNX model integration, grammar rules, contextual confusion detection, correction merging, overlap removal, priority ordering, personal dictionary filtering, cloud API fallback
- **Grammar rules** — doubled words, a/an usage, capitalization after periods, subject-verb agreement, its/it's, missing punctuation
- **Context rules** — their/there/they're, your/you're, to/too, then/than with position accuracy checks
- **Stores** — editor state, document management, session handling, settings persistence, capture mode, mind map, polish mode, scaffold, format
- **Hooks** — snapshot engine for passive learning, voice input, media recording, read-aloud TTS, frustration detection
- **UI components** — sidebar, topbar, app layout, voice bar, font selector, dialog, toast, loading spinner, empty state, corrections panel, polish panel, settings tabs
- **API client** — token persistence, retry logic, request cancellation, error handling

---

## Backend Tests

22 test files covering the API endpoints, core logic, and service integrations.

```bash
cd backend

# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_adaptive_loop.py
pytest tests/test_llm_orchestrator.py
pytest tests/test_error_profile.py

# Run tests matching a keyword
pytest tests/ -k "adaptive"
pytest tests/ -k "correction"

# Type checking and linting
mypy app/ --ignore-missing-imports
ruff check app/
```

### What's Covered

- **Adaptive learning loop** — tokenization, word-level diff (LCS), similarity scoring, Levenshtein distance, error type classification, letter reversal detection, phonetic similarity, homophone detection, omission/addition detection, snapshot pair processing
- **LLM orchestrator** — two-tier routing logic, deep analysis triggering, correction merging, quick-only and deep-only modes, auto-routing, document review
- **Error profiles** — user error pattern storage and retrieval
- **Corrections API** — endpoint request/response handling
- **Quick correction** — model integration and error logging
- **Repositories** — database CRUD operations and error handling
- **Prompt builder** — dynamic prompt construction with user error profiles
- **LLM tools** — tool calling and function integration
- **NIM client** — NVIDIA NIM API integration
- **Voice system** — speech-to-text service, idea extraction, capture prompts
- **Vision** — image-to-thought-card extraction and prompt construction
- **TTS** — text-to-speech service integration
- **User settings and privacy** — settings persistence and privacy endpoint handling
- **Progress tracking** — dashboard data repository
- **Seed data** — database initialization

---

## Progress Dashboard Testing

```bash
# Backend
cd backend
pytest tests/test_progress_repo.py -v

# Frontend
cd frontend
npm test -- --testPathPattern=ProgressDashboard
```

### Dashboard Testing Checklist

- [ ] Dashboard loads without errors at `/progress`
- [ ] Loading state appears briefly
- [ ] All sections render (streaks, mastered words, trends, charts)
- [ ] Empty states show for new users
- [ ] Charts display data when available
- [ ] Theme switching works (cream, night)
- [ ] Responsive on desktop, tablet, and mobile
- [ ] Keyboard navigation and screen reader support
- [ ] WCAG AA color contrast met
- [ ] No console errors

### Testing With Sample Data

```bash
# Get dashboard data via API (requires auth token)
curl -X GET "http://localhost:8000/api/v1/progress/dashboard?weeks=12" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" | jq
```

---

## ONNX Model Test Results

Results from testing against 39 hand-crafted dyslexic writing samples across 8 error categories.

### Error Detection (ONNX Token Classification)

The ONNX model runs in-browser at ~2.6ms per sentence. Its job is to **detect** which words contain errors.

| Category | Samples | Recall | Precision | Avg Latency |
|---|---|---|---|---|
| Letter reversals | 7 | **100%** | 87.5% | 2.23ms |
| Transpositions | 5 | **100%** | 100% | 2.68ms |
| Phonetic | 6 | **100%** | 93.8% | 2.61ms |
| Omissions | 5 | **100%** | 100% | 2.77ms |
| Homophones | 4 | 77.8% | 87.5% | 2.84ms |
| Insertions | 2 | **100%** | 100% | 2.98ms |
| Mixed/severe | 6 | 90.7% | 97.5% | 3.02ms |
| Clean text | 4 | **100%** | 100% | 2.26ms |
| **OVERALL** | **39** | **94.6%** | **96.3%** | **2.64ms** |

Key: Zero false positives on clean text. 100% recall on reversals, transpositions, phonetic errors, omissions, and insertions.

### Error Correction (Seq2Seq T5-small)

The T5-small seq2seq model generates corrected text at ~47ms per sentence.

| Category | Exact Match | Fix Rate | Avg Latency |
|---|---|---|---|
| Letter reversals | 28.6% | 57.1% | 41.8ms |
| Transpositions | 20.0% | 42.9% | 45.2ms |
| Phonetic | 50.0% | 60.0% | 44.1ms |
| Omissions | 60.0% | 69.2% | 42.5ms |
| Homophones | 0.0% | 44.4% | 45.1ms |
| Insertions | 50.0% | 85.7% | 38.4ms |
| Mixed/severe | 0.0% | 17.1% | 56.1ms |
| Clean text | 100% | N/A | 56.5ms |
| **OVERALL** | **35.9%** | **42.5%** | **46.6ms** |

### What Worked

| Input | Output |
|---|---|
| Teh cat sat on teh mat... | The cat sat on the mat... |
| He rode his dike to school... | He rode his bike to school... |
| I had enuff food for dinner last nite. | I had enough food for dinner last night. |
| The goverment announced new rules... | The government announced new rules... |
| She finallly finished her homeworkk... | She finally finished her homework... |

### What Failed

| Input | Got | Problem |
|---|---|---|
| She bought a new bed for her daby. | ...her brother. | Hallucinated a different word |
| Waht si teh porbelm with tihs computer? | Whehet the computer? | Collapsed under heavy errors |
| I dint no wat teh teecher sed... | I forgot to turn on the desk... | Too many errors, rewrote entirely |

### Analysis

The two-tier architecture is validated:
- **Tier 1 (ONNX)** excels at detection — 94.6% recall at 2.6ms with near-zero false positives
- **Tier 1 (Seq2Seq)** handles simple corrections well but breaks on severe mixed errors
- **Tier 2 (Nemotron LLM)** is needed for severe mixed errors, homophones, and cases where seq2seq hallucinates

**Recommendations:** Route severe errors (4+ per sentence) directly to Tier 2. Use dictionary for detected reversals instead of seq2seq. Add confidence threshold to catch hallucinations.

---

## DysLex AI vs Grammarly

| Category | Winner | Why |
|---|---|---|
| **Dyslexia-specific accuracy** | DysLex AI | 100% on reversals, phonetics, transpositions vs. documented failures |
| **General GEC breadth** | Grammarly | Covers grammar, style, tone, plagiarism — broader scope |
| **Latency** | Tie | Both sub-100ms; DysLex AI faster on token classification (2-15ms) |
| **Model efficiency** | DysLex AI | 60M params vs 1B; runs in any browser vs native app |
| **Privacy** | DysLex AI | Local-first, open source, self-hosted |
| **Personalization** | DysLex AI | Passive learning with deep error profiling vs accept/reject buttons |
| **Cost** | DysLex AI | Free (Apache 2.0) vs $12-30/month |
| **False positive rate** | DysLex AI | 0% on clean text vs documented over-flagging |
| **Accessibility design** | DysLex AI | Purpose-built for dyslexic users; invisible corrections, positive framing |
| **Ecosystem/polish** | Grammarly | Mature product, browser extensions, mobile apps |

### Key Metrics Comparison

| Metric | DysLex AI | Grammarly |
|---|---|---|
| Error detection F1 | **99.19%** | 50-75% (independent tests) |
| False positives on clean text | **0.00%** | Documented over-flagging |
| Model size | ~130 MB (quantized) | ~300 MB on-device |
| Runs in browser | Yes (any browser) | Native app only |
| Per-user error profile | Yes (passive) | No dyslexia-specific tracking |
| Individual cost | **$0** | $12-30/month |
| Classroom (30 students) | **$0** | $360-900/month |

### Documented Grammarly Failures for Dyslexic Users

- **University for the Creative Arts (2021):** "The errors typical of dyslexic writers are phonetically spelled or atypical errors that are difficult for traditional tools such as Grammarly to catch."
- **User report:** Grammarly suggested "wedding" for "weeding" in a gardening context.
- **Academic study (PMC, 2024):** Grammarly "tends to over-flag issues resulting in many false positives."

### Data Sources

**DysLex AI:** `ml/quick_correction/models/*/eval_report.json`, `ml/quick_correction/benchmark.py`

**Grammarly:** [On-Device AI at Scale](https://www.grammarly.com/blog/engineering/on-device-models-scale/) (2025), [GECToR GitHub](https://github.com/grammarly/gector), [Pillars of GEC (BEA-2024)](https://arxiv.org/html/2404.14914v1), [UCA Blog](https://ucalearningandteaching.wordpress.com/2021/03/17/using-grammarly-to-help-students-with-dyslexia/), [PMC Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11327564/)

---

## Reproducing Results

```bash
# Full dyslexic test suite
python ml/quick_correction/test_dyslexic.py

# With sample-level details
python ml/quick_correction/test_dyslexic.py --verbose

# Save JSON report
python ml/quick_correction/test_dyslexic.py --output results.json
```

**Test environment:** macOS (Apple Silicon arm64), T5-small (~60M params) PyTorch, DistilBERT (~66M params) ONNX Runtime, 39 hand-crafted sentences across 8 categories.
