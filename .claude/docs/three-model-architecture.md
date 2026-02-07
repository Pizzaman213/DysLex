# Three-Model Architecture

## Purpose

DysLex AI uses three interconnected models to provide intelligent, personalized writing assistance. Each model handles a specific job, and they pass information between each other to create a system that genuinely improves with every use.

The key insight: no single model can do everything well. Fast local models can't understand context. Powerful cloud models are too slow for real-time typing. Static databases can't adapt. By combining all three, we get the best of each.

## The Three Models

### Model 1: User Error Profile (The Adaptive Brain)

**What it is**: A PostgreSQL database that builds a fingerprint of each user's specific dyslexic error patterns.

**Why it matters**: Every person with dyslexia makes different mistakes. Some reverse b/d constantly. Others struggle with homophones. Some have phonetic substitution patterns. This model captures those unique patterns.

**What it stores**:
| Data Point | Example | Purpose |
|------------|---------|---------|
| Error Frequency Map | "becuase" → "because" (47 times) | Prioritize common errors |
| Error Type Classification | Reversal: 34%, Phonetic: 28% | Tell LLM what to look for |
| Confusion Pairs | their/there/they're | Catch real-word errors |
| Improvement Tracking | "teh" errors: 15/week → 3/week | Adjust focus over time |
| Context Patterns | More errors in long documents | Adjust correction aggressiveness |

**Key files**:
- `backend/app/db/models.py` — SQLAlchemy ORM models
- `backend/app/core/error_profile.py` — Profile logic
- `database/schema/init.sql` — PostgreSQL schema

### Model 2: Quick Correction Model (The Fast Local Fixer)

**What it is**: A small language model (~100M-500M params) that runs directly in the user's browser via ONNX Runtime Web.

**Why it matters**: For common errors, users need instant feedback. No network latency, no API costs. The correction appears before they finish typing the next word.

**Latency target**: Under 50ms per correction.

**How it works**:
1. User types text
2. ONNX model runs inference in browser
3. Known error patterns are caught immediately
4. Corrections appear inline without any API call

**Personalization**: The model uses a small adapter layer that's updated based on the user's Error Profile. When the profile updates, the adapter retrains in the background (takes seconds, not hours).

**Key files**:
- `frontend/src/services/onnxModel.ts` — Browser inference
- `ml/quick_correction/train.py` — Training script
- `ml/quick_correction/export_onnx.py` — ONNX export

### Model 3: Deep Analysis LLM (The Smart Contextual Engine)

**What it is**: A large language model (Nemotron via NVIDIA NIM) that understands full context.

**Why it matters**: Some errors require understanding what the user meant to say:
- Real-word errors (using "bark" when they meant "park")
- Homophones in wrong context ("there car" vs "their car")
- Severely misspelled words where intent must be inferred
- Grammar issues specific to dyslexic patterns

**Two-tier processing**:
| Tier | Model | When Used | Latency |
|------|-------|-----------|---------|
| Tier 1 | Nemotron-3-Nano (NIM API) | Common errors, real-time | <500ms |
| Tier 2 | Nemotron-3-Nano-30B-A3B | Complex analysis, full document | 1-5s |

**Key files**:
- `backend/app/core/llm_orchestrator.py` — Routing logic
- `backend/app/services/nim_client.py` — NIM API client
- `backend/app/services/nemotron_client.py` — Deep analysis

## How They Work Together

```
User Types → Quick Correction Model (instant)
                ↓
         Error Profile (personalization)
                ↓
         Deep Analysis LLM (when needed)
                ↓
         Corrections appear inline
                ↓
         User behavior observed
                ↓
         Error Profile updates
                ↓
         Quick Correction Model improves
```

The feedback loop is continuous. The more someone writes, the smarter their personal instance becomes.

## Technical Implementation

### Frontend
- `Editor.tsx` captures text and triggers local ONNX inference
- `usePassiveLearning.ts` takes snapshots for the learning loop
- `correctionService.ts` orchestrates local vs cloud corrections

### Backend
- `llm_orchestrator.py` decides Tier 1 vs Tier 2
- `error_profile.py` manages per-user patterns
- `adaptive_loop.py` processes behavioral signals

### Database
- `error_profiles` table stores per-user patterns (JSONB)
- `error_logs` table stores individual corrections
- `confusion_pairs` table stores language-specific homophones

## Status

- [x] Designed
- [x] Database schema implemented
- [x] Backend structure implemented
- [ ] ONNX model training pipeline
- [ ] NIM API integration complete
- [ ] Full loop tested end-to-end
