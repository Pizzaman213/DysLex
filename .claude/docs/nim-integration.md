# NVIDIA NIM Integration

## Purpose

DysLex AI uses NVIDIA NIM (NVIDIA Inference Microservices) for AI-powered features. NIM provides optimized, production-ready endpoints for LLMs, text-to-speech, and speech-to-text.

## Services Used

| Service | NIM Endpoint | Purpose |
|---------|--------------|---------|
| Nemotron-3-Nano | Chat completions | Tier 1 quick corrections |
| Nemotron-3-Nano-30B-A3B | Chat completions | Tier 2 deep analysis |
| MagpieTTS Multilingual | Audio synthesis | Text-to-speech read-aloud |
| faster-whisper | Audio transcription | Speech-to-text voice input |

## Configuration

### Environment Variables

```bash
# Required
NVIDIA_NIM_API_KEY=nvapi-xxxxxxxxxxxx

# Optional (defaults shown)
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
```

### Settings

```python
# backend/app/config.py
class Settings(BaseSettings):
    nvidia_nim_api_key: str = ""
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
```

## API Clients

### Base NIM Client

```python
# backend/app/services/nim_base.py
import httpx

class NIMClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    async def request(self, endpoint: str, payload: dict, timeout: float = 30.0):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/{endpoint}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
```

### Chat Completions (LLM)

```python
# backend/app/services/nim_client.py
async def chat_completion(messages: list, model: str = "nvidia/nemotron-mini-4b-instruct"):
    """Call NIM chat completions endpoint."""
    return await nim_client.request(
        "chat/completions",
        {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.1,
        },
    )
```

### Audio Synthesis (TTS)

```python
# backend/app/services/tts_service.py
async def synthesize_speech(text: str, voice: str = "default"):
    """Call NIM audio synthesis endpoint."""
    return await nim_client.request(
        "audio/speech",
        {
            "model": "nvidia/magpietts",
            "input": text,
            "voice": voice,
            "response_format": "mp3",
        },
    )
```

### Audio Transcription (STT)

```python
# backend/app/services/stt_service.py
async def transcribe_audio(audio_file: bytes):
    """Call NIM audio transcription endpoint."""
    # faster-whisper endpoint
    # Returns transcript with optional timestamps
```

## Models Available

### Nemotron-3-Nano (Mini)
- **Model ID**: `nvidia/nemotron-mini-4b-instruct`
- **Parameters**: ~4B
- **Use case**: Fast, cost-effective corrections
- **Latency**: <500ms

### Nemotron-3-Nano-30B-A3B
- **Model ID**: `nvidia/nemotron-3-nano-30b-a3b`
- **Parameters**: 31.6B total, ~3.6B active (MoE)
- **Use case**: Deep analysis, complex inference
- **Latency**: 1-5s
- **Special**: Supports reasoning ON/OFF modes

### MagpieTTS
- **Model ID**: `nvidia/magpietts`
- **Languages**: English, Spanish, German, French, Vietnamese, Italian, Chinese
- **Quality**: Natural, human-like prosody

### faster-whisper
- **Model**: Whisper large-v3 optimized
- **Languages**: 100+
- **Features**: Word-level timestamps

## Self-Hosting Option

For privacy-critical deployments, Nemotron can be self-hosted:

### Via NVIDIA Brev
```bash
# One-click deployment with auto-scaling
brev deploy nvidia/nemotron-3-nano-30b-a3b
```

### Via Docker
```yaml
# docker-compose.yml (optional self-hosted)
services:
  dyslex-llm:
    image: nvcr.io/nvidia/nemotron:latest
    runtime: nvidia
    environment:
      - MODEL=nemotron-3-nano-30b-a3b
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Hardware Requirements (Self-Hosted)
- GPU: RTX 4090 or better
- VRAM: 24GB+
- Quantization: FP8 for efficiency

## Error Handling

```python
async def nim_request_safe(endpoint: str, payload: dict):
    """NIM request with error handling."""
    try:
        return await nim_client.request(endpoint, payload)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            # Rate limited - implement backoff
            await asyncio.sleep(1)
            return await nim_request_safe(endpoint, payload)
        elif e.response.status_code == 401:
            raise ValueError("Invalid NVIDIA NIM API key")
        raise
    except httpx.ConnectError:
        raise ConnectionError("Cannot reach NVIDIA NIM API")
```

## Rate Limits & Quotas

| Tier | Requests/min | Tokens/min |
|------|--------------|------------|
| Free | 10 | 10,000 |
| Standard | 100 | 100,000 |
| Enterprise | Unlimited | Unlimited |

## Key Files

- `backend/app/config.py` — NIM configuration
- `backend/app/services/nim_client.py` — LLM client
- `backend/app/services/tts_service.py` — TTS client
- `backend/app/services/stt_service.py` — STT client
- `backend/app/services/nemotron_client.py` — Deep analysis

## Security

- API key stored as environment variable
- Never logged or exposed in responses
- HTTPS only for all NIM calls
- Audio/text not stored by NIM after processing

## Status

- [x] Configuration structure
- [x] Client placeholders
- [ ] Full NIM LLM integration
- [ ] MagpieTTS integration
- [ ] faster-whisper integration
- [ ] Self-hosted option tested
- [ ] Rate limit handling
