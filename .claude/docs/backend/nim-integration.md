# NVIDIA NIM Integration

## Purpose

DysLex AI uses NVIDIA NIM for LLM corrections and MagpieTTS. The architecture is **ONNX-first** — local models handle most corrections, with NIM API as the Tier 2 deep analysis layer.

## Services Used

| Service | Implementation | Purpose |
|---------|---------------|---------|
| Nemotron (NIM API) | `nemotron_client.py` | Tier 2 deep analysis |
| MagpieTTS (Riva TTS) | `tts_service.py` + `grpc_tts_client.py` | Text-to-speech |
| Local ONNX (DistilBERT) | `quick_correction_service.py` | Tier 1 quick corrections |

**Note**: STT (speech-to-text) uses browser Web Speech API, not a backend service.

## Configuration

`backend/app/config.py`:

```python
nvidia_nim_api_key: str = ""           # Required for NIM API
nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
nvidia_nim_model: str = "nvidia/llama-3.1-nemotron-nano-8b-v1"
nvidia_nim_voice_url: str = ""         # Cloud or self-hosted Riva URL
```

## NIM API Client

`backend/app/services/nemotron_client.py`:
- HTTP POST to NIM chat/completions endpoint
- Retry with tenacity (3 attempts, exponential backoff)
- Tool calling support (up to 3 rounds)
- Circuit breaker protection
- Chunked processing for long documents

## TTS Architecture

Two protocols supported, auto-detected by URL:

| Protocol | When | Client |
|----------|------|--------|
| **gRPC** | Cloud API (`integrate.api.nvidia.com`) | `grpc_tts_client.py` |
| **HTTP** | Self-hosted Riva NIM | `tts_service.py` direct |

`tts_service.py` handles:
- Content-addressed caching (SHA-256 hash → WAV file)
- Batch synthesis for multiple sentences
- Voice mapping (friendly IDs → Riva voice names)
- `.meta` files for cache cleanup

Available voices: `default`/`aria` (EN-US), `diego` (ES-US), `louise` (FR-FR)

## Key Files

| File | Role |
|------|------|
| `backend/app/config.py` | NIM configuration |
| `backend/app/services/nemotron_client.py` | Deep analysis NIM client |
| `backend/app/services/nim_client.py` | Tier 1 wrapper (delegates to ONNX) |
| `backend/app/services/tts_service.py` | TTS with auto-detect cloud/self-hosted |
| `backend/app/services/grpc_tts_client.py` | Cloud gRPC TTS client |
| `backend/app/services/quick_correction_service.py` | Local ONNX corrections |

## Integration Points

- [LLM Orchestrator](llm-orchestrator.md): Routes between Tier 1/2
- [Circuit Breaker](../core/circuit-breaker.md): Protects NIM calls
- [TTS](text-to-speech.md): Voice synthesis details
- [ONNX Correction](../frontend/onnx-local-correction.md): Local model details

## Status

- [x] NIM API client with retry + circuit breaker
- [x] ONNX-first architecture (local model as Tier 1)
- [x] MagpieTTS with cloud gRPC + self-hosted HTTP
- [x] Content-addressed TTS caching
- [x] Tool calling support
- [ ] faster-whisper NIM integration for STT
- [ ] Self-hosted Nemotron testing
