# Three-Model Architecture

## Purpose

DysLex AI uses three interconnected models. Each handles a specific job, and they pass information between each other to create a system that improves with every use.

## The Three Models

### Model 1: User Error Profile (PostgreSQL)

Per-user database tracking individual error patterns via normalized tables.

**Key files:**
- `backend/app/core/error_profile.py` — `ErrorProfileService` with Redis-cached profile assembly
- `backend/app/db/models.py` — `UserErrorPattern`, `UserConfusionPair`, `PersonalDictionary`, `ErrorLog`
- `backend/app/db/repositories/user_error_pattern_repo.py` — Pattern CRUD with upsert

### Model 2: Quick Correction Model (ONNX)

Small model running in browser (frontend) and server (backend) for sub-50ms corrections.

**Frontend (browser):** `frontend/src/services/onnxModel.ts` — T5 seq2seq + SymSpell + Double Metaphone fallback chain
**Backend (server):** `backend/app/services/quick_correction_service.py` — DistilBERT ONNX with per-user adapters

### Model 3: Deep Analysis LLM (NVIDIA NIM)

Nemotron via NIM API for context-aware corrections and full-document review.

**Key files:**
- `backend/app/services/nemotron_client.py` — Chunked deep analysis with circuit breaker
- `backend/app/core/llm_orchestrator.py` — Two-tier routing (quick → deep)
- `backend/app/core/prompt_builder.py` — `build_correction_prompt_v2()` with full `LLMContext`

## How They Work Together

```
User Types → Quick Correction (Tier 1, <50ms)
                ↓ flagged corrections
         Deep Analysis (Tier 2, 1-5s)
                ↓
         Corrections merged (deep wins at overlapping positions)
                ↓
         User behavior observed (passive snapshots)
                ↓
         Error Profile updates → both models improve
```

## Key Files

| Layer | File | Role |
|-------|------|------|
| Orchestrator | `backend/app/core/llm_orchestrator.py` | `auto_route()` — confidence-based tier selection |
| Tier 1 | `backend/app/services/nim_client.py` | Delegates to `QuickCorrectionService` |
| Tier 2 | `backend/app/services/nemotron_client.py` | NIM API with chunking + circuit breaker |
| Profile | `backend/app/core/error_profile.py` | `build_llm_context()` for prompt enrichment |
| Prompts | `backend/app/core/prompt_builder.py` | `build_correction_prompt_v2()` returns (system, user) |
| Frontend ONNX | `frontend/src/services/onnxModel.ts` | T5 seq2seq with dictionary fallback |

## Status

- [x] Error Profile with normalized tables and Redis caching
- [x] Quick Correction (ONNX) on frontend and backend
- [x] Deep Analysis via NIM API with chunking
- [x] Two-tier orchestrator with confidence routing
- [x] Circuit breaker protection for NIM calls
- [ ] Per-user ONNX adapter retraining pipeline
- [ ] End-to-end loop tested at scale
