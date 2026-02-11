# ONNX Local Correction Model

## Purpose

Browser-based spelling correction using a T5 seq2seq ONNX model with multiple fallback layers. Provides sub-50ms corrections without network calls.

## Fallback Chain

`frontend/src/services/onnxModel.ts` tries corrections in order:

1. **T5 seq2seq model** — ONNX Runtime Web inference in browser
2. **User + base dictionary lookup** — Known misspelling→correction pairs
3. **SymSpell edit-distance** — Edit distance 2 fuzzy matching
4. **Double Metaphone** — Phonetic similarity matching

If all fail, the word is left uncorrected (Tier 2 deep analysis handles it).

## Key Exports

| Export | Purpose |
|--------|---------|
| `loadModel()` | Load T5 pipeline + base dictionary |
| `runLocalCorrection(text)` | Generate corrections for text |
| `addToLocalDictionary(word)` | Persist word to skip list |
| `updateUserDictionary(entries)` | Load user error profile entries |
| `isModelLoaded()` / `getModelState()` | State queries |

## Error Classification

The model classifies each correction into error types:
- **Omission** — Missing letters
- **Insertion** — Extra letters
- **Transposition** — Swapped adjacent letters
- **Substitution** — Wrong letter
- **Phonetic** — Sounds-like error
- **Spelling** — General spelling error

Algorithm: Edit operation analysis + length comparison. Proper name detection prevents false positives.

## Features

- **Personal dictionary** — Persisted in localStorage, synced from backend
- **Levenshtein similarity scoring** — Skips corrections with <0.3 similarity
- **Capitalization preservation** — Maintains original casing
- **Base dictionary fallback** — Works even if ONNX model fails to load

## Backend Counterpart

`backend/app/services/quick_correction_service.py`:
- DistilBERT ONNX model (server-side)
- Per-user adapter loading from `ml/models/adapters/{user_id}_v1.onnx`
- 60-second TTL caching

## Key Files

| File | Role |
|------|------|
| `frontend/src/services/onnxModel.ts` | Browser ONNX inference + fallbacks |
| `backend/app/services/quick_correction_service.py` | Server-side ONNX corrections |
| `backend/app/services/nim_client.py` | Thin wrapper delegating to quick service |
| `ml/quick_correction/train.py` | Model training script |
| `ml/quick_correction/export_onnx.py` | ONNX export script |
| `ml/quick_correction/train_seq2seq.py` | T5 seq2seq training |

## Integration Points

- [Draft Mode](../modes/draft-mode.md): Calls `loadModel()` on mount, `runLocalCorrection()` for corrections
- [LLM Orchestrator](../backend/llm-orchestrator.md): Tier 1 via `nim_client.py`
- [Error Profile](../core/error-profile-system.md): User dictionary entries loaded

## Status

- [x] T5 seq2seq ONNX model in browser
- [x] SymSpell + Double Metaphone fallbacks
- [x] Error classification by type
- [x] Personal dictionary with persistence
- [x] Server-side DistilBERT counterpart
- [ ] Per-user adapter retraining pipeline
- [ ] Model versioning and updates
