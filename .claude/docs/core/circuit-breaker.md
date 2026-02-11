# Circuit Breaker

## Purpose

Protects DysLex AI from cascading failures when the NVIDIA NIM API is unavailable. Prevents overwhelming a failing service with retries and provides fast fallback to local corrections.

## Implementation

`backend/app/core/circuit_breaker.py` implements an async-safe circuit breaker with three states:

```
CLOSED (normal) → failures hit threshold → OPEN (rejecting all calls)
                                              ↓ cooldown expires
                                          HALF_OPEN (probe one call)
                                              ↓ success → CLOSED
                                              ↓ failure → OPEN (longer cooldown)
```

### Configuration

From `backend/app/config.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `circuit_breaker_failure_threshold` | 3 | Failures before opening |
| `circuit_breaker_cooldown_seconds` | 60 | Seconds before probing |

### Key Classes

- `CircuitState` — Enum: `CLOSED`, `OPEN`, `HALF_OPEN`
- `CircuitBreakerOpen` — Exception raised when circuit is open (callers catch this)
- `CircuitBreaker` — Main class with `call()` async context manager

Thread safety is ensured via `asyncio.Lock`. The breaker uses exponential backoff on repeated failures.

## Usage in Codebase

The circuit breaker wraps NIM API calls in `nemotron_client.py`:

```python
# backend/app/services/nemotron_client.py
async def _call_nim_api(...):
    # Circuit breaker protects this call
    # On CircuitBreakerOpen: return empty corrections (graceful degradation)
```

The LLM orchestrator (`llm_orchestrator.py`) catches `CircuitBreakerOpen` and degrades gracefully — returning only Tier 1 (local ONNX) corrections when Tier 2 is unavailable.

## Key Files

| File | Role |
|------|------|
| `backend/app/core/circuit_breaker.py` | `CircuitBreaker` class |
| `backend/app/services/nemotron_client.py` | Uses breaker for NIM API calls |
| `backend/app/core/llm_orchestrator.py` | Catches `CircuitBreakerOpen` for graceful degradation |
| `backend/app/config.py` | Threshold and cooldown configuration |
| `backend/tests/test_circuit_breaker.py` | Unit tests |

## Status

- [x] Circuit breaker with CLOSED/OPEN/HALF_OPEN states
- [x] Async-safe with asyncio.Lock
- [x] Integrated into nemotron_client
- [x] Graceful degradation in orchestrator
- [x] Unit tests
