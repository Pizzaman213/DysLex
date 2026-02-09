# DysLex AI

**An open-source, adaptive AI writing tool built for dyslexic thinkers.**

Dyslexia isn't a deficit -- it's a different cognitive architecture. Dyslexic thinkers often excel at big-picture reasoning, pattern recognition, and creative problem-solving. The challenge isn't a lack of ideas; it's that traditional writing tools create friction between brilliant thinking and the page. DysLex AI removes that friction.

## Built with NVIDIA NIM

DysLex AI is powered by [NVIDIA NIM](https://build.nvidia.com/) inference microservices:

| Product | Model ID | Role |
|---|---|---|
| **Nemotron-3-Nano-30B-A3B** | `nvidia/nemotron-3-nano-30b-a3b` | Deep text analysis -- context-aware corrections, homophones, real-word errors, intent inference |
| **Cosmos Reason2 8B** | `nvidia/cosmos-reason2-8b` | Vision-based idea extraction -- converts uploaded images and diagrams into thought cards |
| **MagpieTTS Multilingual** | `nvidia/magpietts` | Natural text-to-speech -- read-aloud with voices in English, Spanish, French, and more |
| **faster-whisper** | Whisper large-v3 (optimized) | Speech-to-text transcription -- real-time voice input for Capture Mode |

All cloud services are accessed through a single NVIDIA NIM API key via `https://integrate.api.nvidia.com/v1`.

## How It Works

DysLex AI combines three models that no one has put together properly before:

| Model | Role | Runs |
|---|---|---|
| **Error Profile** | Learns each user's unique spelling/grammar patterns over time | PostgreSQL (server) |
| **Quick Correction** | Instant fixes for known errors -- no network round-trip | ONNX Runtime (browser) |
| **Deep Analysis** | Context-aware correction for homophones, real-word errors, intent inference | NVIDIA Nemotron (cloud) |

These models feed into each other through a **passive learning loop** -- the system observes natural writing behavior (self-corrections, repeated errors, word rewrites) without ever asking the user to accept or reject anything. No pop-ups. No interruptions. It just gets smarter.

## Four Writing Modes

- **Capture** -- Speak freely. Voice is transcribed and organized into draggable thought cards.
- **Mind Map** -- Arrange ideas visually. AI suggests connections and identifies gaps.
- **Draft** -- Write with a scaffolded editor, inline corrections, and an AI coach. Passive learning runs silently.
- **Polish** -- Review tracked changes, readability scores, and structural suggestions with plain-English explanations.

## Design Principles

- **Voice-first, text-second.** Voice input is a first-class citizen, not an afterthought.
- **Structure emerges, not imposed.** Let ideas flow, then help organize them.
- **Corrections are invisible.** Never interrupt creative flow.
- **Show progress, not deficits.** "500 words written today" -- never "23 errors found."
- **Respect the person.** The user is intelligent. They need better tools, not simpler ideas.

## Quick Start

```bash
# One command to start everything (recommended)
python3 run.py --auto-setup

# Or run services individually
cd frontend && npm install && npm run dev    # port 3000
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload  # port 8000

# Or use Docker
docker compose -f docker/docker-compose.yml up
```

**Prerequisites:** Node.js 20+, Python 3.11+, PostgreSQL 15+

## Tech Stack

**Frontend:** React 18, TipTap, TypeScript, Vite, Zustand, ONNX Runtime Web
**Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic 2.0
**Database:** PostgreSQL 15+
**ML/AI:** NVIDIA NIM (Nemotron), MagpieTTS, faster-whisper
**Infra:** Docker, Nginx

## Documentation

- [Architecture](docs/architecture.md) -- System design overview
- [API Reference](docs/api-reference.md) -- Endpoint documentation
- [Database Schema](docs/database-schema.md) -- ERD and table docs
- [ML Models](docs/ml-models.md) -- Model architecture and training
- [Deployment](docs/deployment.md) -- Production setup
- [Contributing](docs/contributing.md) -- How to get involved
- [run.py Guide](RUN_PY_GUIDE.md) -- Launcher documentation

## License

Apache 2.0 -- See [LICENSE](LICENSE)

Dyslexia affects roughly 1 in 5 people worldwide. A tool this powerful should not be locked behind a paywall.

---

*"Everyone has ideas worth sharing. The right tool just makes sharing them easier."*
