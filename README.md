# DysLex AI

**An open-source, adaptive AI writing tool built for dyslexic thinkers.**

Dyslexia isn't a deficit — it's a different cognitive architecture. DysLex AI removes the friction between brilliant thinking and the page.

---

## Features

- **Per-user adaptive error profiling** — learns your unique spelling and grammar patterns over time
- **Instant local corrections** — small ONNX model runs in-browser, under 50ms, works offline
- **Deep contextual analysis** — catches homophones, real-word errors, and severe misspellings via NVIDIA Nemotron
- **Passive learning** — no accept/reject buttons; the system learns silently from your natural writing behavior
- **Voice-first input** — real-time transcription with idea extraction via faster-whisper
- **Text-to-speech** — hear your writing read back to you via MagpieTTS
- **Vision input** — upload handwritten notes, diagrams, or whiteboard photos
- **Four writing modes** — Capture (voice-to-thought), Mind Map, Draft (scaffolded writing), Polish (review and refine)
- **Dyslexia-friendly design** — specialized fonts, eye-friendly colors, invisible corrections, no deficit framing

---

## Quick Start

```bash
# One command to start everything
python3 run.py --auto-setup
```

This starts PostgreSQL, Redis, the backend (port 8000), and frontend (port 3000) automatically.

```bash
# Or run manually
cd frontend && npm install && npm run dev       # port 3000
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload  # port 8000

# Or use Docker
docker compose -f docker/docker-compose.yml up
```

**Prerequisites:** Python 3.11+, Node.js 20+, PostgreSQL 15+, Redis — see [Quickstart Guide](docs/quickstart.md) for details.

---

## How It Works

| Model | What It Does | Where It Runs |
|-------|-------------|---------------|
| **Error Profile** | Learns each user's unique error patterns over time | PostgreSQL (server) |
| **Quick Correction** | Instant fixes for known errors — no network needed | ONNX Runtime (browser) |
| **Deep Analysis** | Context-aware correction for homophones, real-word errors, intent | NVIDIA Nemotron (cloud) |

These three models feed into each other through a **passive learning loop** — the system observes natural writing behavior without ever asking the user to accept or reject anything. See [How It Works](docs/how-it-works.md) for the full architecture.

---

## Tech Stack

**Frontend:** React 18, TipTap, TypeScript, Vite, Zustand, ONNX Runtime Web
**Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic 2.0
**ML/AI:** NVIDIA NIM (Nemotron), MagpieTTS, faster-whisper, ONNX Runtime

---

## Documentation

- [Quickstart Guide](docs/quickstart.md) — Prerequisites, setup, environment variables, troubleshooting
- [How It Works](docs/how-it-works.md) — Architecture, passive learning, writing modes, accessibility
- [Testing](docs/testing.md) — ML tests, frontend/backend test suites, benchmarks
- [Architecture](docs/architecture.md) — System design overview
- [API Reference](docs/api-reference.md) — Endpoint documentation
- [Database Schema](docs/database-schema.md) — ERD and table docs
- [ML Models](docs/ml-models.md) — Model architecture and training
- [Deployment](docs/deployment.md) — Production setup
- [Contributing](docs/contributing.md) — How to get involved

---

## License

Apache 2.0 — See [LICENSE](LICENSE)

Dyslexia affects roughly 1 in 5 people worldwide. A tool this powerful should not be locked behind a paywall.

---

*"Everyone has ideas worth sharing. The right tool just makes sharing them easier."*

<!--
4D 61 64 65 20 42 79 20 43 6F 6E 6E 6F 72 20 53 65 63 72 69 73 74 20 46 6F 72 20 4E 76 69 64 69 61 20 47 54 43
-->
