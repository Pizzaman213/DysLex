# LLM Orchestrator — Two-Tier Processing

## Purpose

Routes text corrections through a two-tier system: fast Tier 1 for common errors, deep Tier 2 for complex analysis. Balances speed, cost, and quality.

## Routing Logic

`backend/app/core/llm_orchestrator.py`:

| Function | Behavior |
|----------|----------|
| `quick_only(text, user_id)` | Tier 1 only |
| `deep_only(text, user_id)` | Tier 2 only |
| `auto_route(text, user_id)` | **Primary endpoint** — confidence-based routing |
| `document_review(text, user_id)` | Always Tier 2 (full document) |

### auto_route() Flow

1. Run Tier 1 quick corrections
2. Split results into confident vs flagged
3. Send flagged corrections to Tier 2 for deep analysis
4. Merge results: deep analysis wins at overlapping positions (`_merge_corrections()`)
5. On `CircuitBreakerOpen`: return only Tier 1 results (graceful degradation)

## Tier 1: Quick Corrections

`backend/app/services/nim_client.py` → `backend/app/services/quick_correction_service.py`:
- Delegates to local ONNX model (DistilBERT)
- Returns empty list if model unavailable (triggers Tier 2)
- Sub-50ms latency target

## Tier 2: Deep Analysis

`backend/app/services/nemotron_client.py`:
- NVIDIA NIM API (Nemotron) with chunked processing
- Splits on paragraph/sentence boundaries (max 3000 chars)
- Parallel chunk processing (max 3 concurrent)
- Personalized prompts via `build_correction_prompt_v2()`
- Supports tool calling (up to 3 rounds)
- [Circuit breaker](../core/circuit-breaker.md) protection
- Position adjustment for chunked documents

## Prompt Construction

`backend/app/core/prompt_builder.py`:

| Function | Purpose |
|----------|---------|
| `build_correction_prompt()` | Legacy single-turn prompt |
| `build_correction_prompt_v2(text, llm_context)` | Returns `(system_msg, user_msg)` with full profile |

The v2 prompt includes: top 20 errors, error type breakdown, confusion pairs, grammar patterns, writing level, personal dictionary, mastered words, and improvement trends.

## Key Files

| File | Role |
|------|------|
| `backend/app/core/llm_orchestrator.py` | Routing logic |
| `backend/app/services/nim_client.py` | Tier 1 wrapper |
| `backend/app/services/quick_correction_service.py` | ONNX corrections |
| `backend/app/services/nemotron_client.py` | Tier 2 NIM API |
| `backend/app/core/prompt_builder.py` | Prompt construction |
| `backend/app/core/circuit_breaker.py` | Failure protection |

## Integration Points

- [Error Profile](../core/error-profile-system.md): `build_llm_context()` for prompt enrichment
- [Circuit Breaker](../core/circuit-breaker.md): Protects NIM API calls
- [Draft Mode](../modes/draft-mode.md): Primary consumer via API
- [Polish Mode](../modes/polish-mode.md): `document_review()` for full analysis

## Status

- [x] Two-tier routing with confidence splitting
- [x] Chunked deep analysis with parallel processing
- [x] Personalized prompts via LLMContext
- [x] Circuit breaker integration
- [x] Graceful degradation (Tier 1 only when Tier 2 fails)
- [ ] Correction caching layer
- [ ] Cost tracking per user
