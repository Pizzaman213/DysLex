# LLM Orchestrator — Two-Tier Processing

## Purpose

The LLM Orchestrator routes text corrections through a two-tier system: fast Tier 1 for common errors, and deep Tier 2 for complex analysis. This balances speed, cost, and quality.

**Key insight**: Most corrections don't need a 30B model. Save the heavy lifting for when it matters.

## Two-Tier Architecture

### Tier 1: Quick Corrections
- **Model**: NVIDIA NIM API (Nemotron-3-Nano) or local ONNX
- **Latency**: <500ms
- **Use cases**: Common misspellings, known patterns, real-time typing

### Tier 2: Deep Analysis
- **Model**: Nemotron-3-Nano-30B-A3B (self-hosted or Brev)
- **Latency**: 1-5 seconds
- **Use cases**: Complex real-word errors, full-document review, intent inference

## When Each Tier Is Used

| Scenario | Tier | Why |
|----------|------|-----|
| User typing "teh" | Tier 1 | Common, known pattern |
| User types "I red the book" | Tier 2 | Real-word error needs context |
| User pauses for 3 seconds | Tier 1 | Quick check of recent text |
| User clicks "Polish" | Tier 2 | Full document analysis |
| Severely garbled text | Tier 2 | Intent inference required |
| Known confusion pair | Tier 1 | Error Profile handles this |

## Technical Implementation

### Orchestrator Logic

```python
# backend/app/core/llm_orchestrator.py

async def get_corrections(text: str, user_id: str, context: str = None) -> list[Correction]:
    """Orchestrate two-tier LLM processing."""
    corrections = []

    # Tier 1: Quick corrections
    quick_results = await quick_correction(text, user_id)
    corrections.extend(quick_results)

    # Tier 2: Deep analysis (if needed)
    if needs_deep_analysis(text, quick_results):
        deep_results = await deep_analysis(text, user_id, context)
        corrections.extend(deep_results)

    # Deduplicate and prioritize
    return deduplicate_corrections(corrections)


def needs_deep_analysis(text: str, quick_results: list[Correction]) -> bool:
    """Determine if text needs deep analysis."""
    # Heuristics:
    # - Long or complex sentences
    # - No quick corrections found (might be missing something)
    # - User explicitly requested deep review
    word_count = len(text.split())
    return word_count > 20 or len(quick_results) == 0


def deduplicate_corrections(corrections: list[Correction]) -> list[Correction]:
    """Remove duplicates, keeping highest confidence."""
    seen = {}
    for c in corrections:
        key = (c.start, c.end)
        if key not in seen or c.confidence > seen[key].confidence:
            seen[key] = c
    return list(seen.values())
```

### Tier 1: NIM API Client

```python
# backend/app/services/nim_client.py

async def quick_correction(text: str, user_id: str) -> list[Correction]:
    """Quick corrections using NVIDIA NIM API."""
    if not settings.nvidia_nim_api_key:
        return []

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.nvidia_nim_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.nvidia_nim_api_key}"},
            json={
                "model": "nvidia/nemotron-mini-4b-instruct",
                "messages": [
                    {"role": "system", "content": "You are a spelling correction assistant."},
                    {"role": "user", "content": f"Find errors in: {text}"},
                ],
                "max_tokens": 500,
                "temperature": 0.1,
            },
            timeout=10.0,
        )
        return parse_corrections(response.json())
```

### Tier 2: Deep Analysis

```python
# backend/app/services/nemotron_client.py

async def deep_analysis(text: str, user_id: str, context: str = None) -> list[Correction]:
    """Deep analysis using Nemotron-3-Nano-30B-A3B."""
    # Load user's error profile for personalized prompt
    profile = await get_user_profile(user_id)

    # Build personalized prompt
    prompt = build_correction_prompt(text, profile.patterns, profile.confusion_pairs, context)

    # Call Nemotron (self-hosted or Brev)
    response = await call_nemotron(prompt)

    return parse_deep_corrections(response)
```

### Prompt Builder

```python
# backend/app/core/prompt_builder.py

def build_correction_prompt(text: str, patterns: list, confusion_pairs: list, context: str = None) -> str:
    """Build personalized correction prompt."""
    prompt = """You are a writing assistant for a person with dyslexia.
Your job is to identify and correct errors while preserving voice and intent.
Be encouraging, never condescending.

USER ERROR PROFILE:
- Common errors: {patterns}
- Confusion pairs: {confusion_pairs}

INSTRUCTIONS:
1. Read the full text and understand intent
2. Identify all errors, prioritizing known patterns
3. Return JSON: [{{"original": "", "suggested": "", "type": "", "explanation": ""}}]

TEXT: {text}
"""
    return prompt.format(patterns=patterns[:20], confusion_pairs=confusion_pairs, text=text)
```

## Key Files

### Backend
- `backend/app/core/llm_orchestrator.py` — Main routing logic
- `backend/app/core/prompt_builder.py` — Prompt construction
- `backend/app/services/nim_client.py` — Tier 1 NIM API
- `backend/app/services/nemotron_client.py` — Tier 2 deep analysis

## Cost Optimization

### Strategies
1. **Use Tier 1 first**: Most corrections don't need Tier 2
2. **Cache common corrections**: "teh" → "the" doesn't need LLM
3. **Batch requests**: Group multiple sentences
4. **Skip known correct words**: User's personal dictionary

### Estimated Costs
| Action | Model | Tokens | Cost |
|--------|-------|--------|------|
| Single sentence | Tier 1 | ~100 | ~$0.0001 |
| Full document | Tier 2 | ~2000 | ~$0.006 |
| Heavy user/month | Mixed | ~50000 | ~$0.15 |

## Error Handling

```python
async def get_corrections_safe(text: str, user_id: str) -> list[Correction]:
    """Get corrections with fallback handling."""
    try:
        return await get_corrections(text, user_id)
    except httpx.HTTPError:
        # NIM API failed, try local model
        return await local_correction(text)
    except Exception as e:
        # Log error, return empty (don't block user)
        logger.error(f"Correction failed: {e}")
        return []
```

## Integration Points

- **Editor**: Triggers correction on pause
- **Error Profile**: Provides personalization data
- **Adaptive Loop**: Receives correction results
- **Frontend**: Displays corrections inline

## Status

- [x] Orchestrator structure designed
- [x] Prompt builder implemented
- [x] NIM client placeholder
- [ ] Nemotron client complete
- [ ] Caching layer
- [ ] Cost tracking
- [ ] Full integration testing
