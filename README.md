# DysLex AI

**An open-source, adaptive AI writing tool built for dyslexic thinkers.**

Dyslexia isn't a deficit -- it's a different cognitive architecture. Dyslexic thinkers often excel at big-picture reasoning, pattern recognition, and creative problem-solving. The challenge isn't a lack of ideas; it's that traditional writing tools create friction between brilliant thinking and the page. DysLex AI removes that friction.

---

## What DysLex AI Does

### Per-User Adaptive Error Profiling

Every person with dyslexia makes different mistakes. DysLex AI builds a unique error fingerprint for each user:

- **Error frequency mapping** -- Tracks exactly which words you misspell and how often (`"becuase" -> "because" (47 times)`, `"teh" -> "the" (112 times)`)
- **Error type classification** -- Breaks down your patterns by category: letter reversals, phonetic substitutions, homophone confusion, letter omissions
- **Confusion pair tracking** -- Learns which word pairs trip you up (their/there/they're, effect/affect, which/witch)
- **Improvement tracking over time** -- Monitors how errors decrease week over week so the system adapts as you improve
- **Context-aware patterns** -- Detects that you make more errors in longer documents or fewer in familiar topics

### Instant Local Corrections (No Internet Required)

A small AI model (~100-500M parameters) runs directly in your browser using ONNX Runtime Web:

- Catches your most common errors instantly -- under 50ms, no network round-trip
- Personalized to your specific error profile, not generic spell-check dictionaries
- Gets retrained on your patterns over time so it improves the more you write
- Works offline -- corrections happen even without an internet connection

### Deep Contextual Analysis

A large language model handles the corrections that no traditional spell checker can:

- **Real-word error detection** -- Catches when you write a real word that's wrong in context ("I went to the bark" -> "park")
- **Homophone resolution** -- Uses full sentence context to pick the right word (their vs. there vs. they're)
- **Severe misspelling recovery** -- Infers intent from heavily misspelled words where traditional tools give up
- **Grammar correction** -- Fixes grammar issues specific to dyslexic writing patterns
- **Plain-English explanations** -- Every correction comes with a friendly, non-condescending explanation of why

### Two-Tier Processing

| Tier | When Used | Speed |
|---|---|---|
| **Tier 1: Quick** | Common errors, known patterns, real-time typing | Under 500ms |
| **Tier 2: Deep** | Complex real-word errors, full-document analysis, intent inference | 1-5 seconds |

The system automatically routes each correction to the right tier -- simple fixes happen instantly, complex ones get deeper analysis.

### Passive Learning (The Secret Sauce)

There are **no accept/reject buttons. No pop-ups. No interruptions.** The system learns by silently observing your natural writing behavior:

| What You Do | What the System Learns |
|---|---|
| You go back and fix your own typo | This is an error you make AND recognize -- catch it earlier next time |
| You leave a flagged word alone across sessions | Might be intentional (name, slang, jargon) -- add to your personal dictionary |
| You rewrite a section and a word changes unexpectedly | Captures your true intent -- high-value training data |
| You write the same misspelling in 5 documents | Persistent error -- prioritize it in the instant correction model |
| An error you used to make stops appearing | You've internalized it -- reduce priority and note improvement in your dashboard |

How it works under the hood:

1. Text snapshots are taken every 5-10 seconds while you type
2. Additional snapshots when you pause for 3+ seconds
3. A background diff engine compares snapshots to detect changes
4. Your error profile updates automatically
5. Corrections improve without you doing anything

### Voice-First Input

Voice is a first-class citizen, not an afterthought:

- **Real-time transcription** -- Powered by faster-whisper (optimized Whisper large-v3)
- **Idea extraction** -- The AI doesn't just transcribe; it identifies key ideas, arguments, examples, and emotional tone from your speech
- **Thought cards** -- Spoken ideas become draggable cards you can rearrange and organize visually
- **Multilingual support** -- Transcription works across multiple languages

### Text-to-Speech Read-Back

Hearing your writing read aloud helps catch errors your eyes miss:

- **Natural voices** -- Powered by MagpieTTS with voices in English, Spanish, French, and more
- **Read-aloud in the editor** -- Highlight any section and hear it spoken back to you
- **Full document playback** -- Listen to your entire piece from start to finish

### Vision-Based Idea Extraction

Upload images, diagrams, handwritten notes, or whiteboard photos:

- **Powered by Cosmos Reason2 8B** -- Converts visual content into structured thought cards
- **Handwriting recognition** -- Turn handwritten brainstorms into digital text
- **Diagram interpretation** -- Extract ideas and relationships from visual diagrams

---

## Four Writing Modes

DysLex AI provides four modes that flow naturally from idea capture through final polish.

### 1. Capture Mode -- Voice-to-Thought

Tap the microphone and speak freely. The AI transcribes in real-time and organizes your ideas into draggable thought cards. Beyond transcription, it identifies key ideas, potential arguments, examples, and emotional tone. You can also upload images of handwritten notes or diagrams to extract ideas visually.

### 2. Mind Map Mode -- Organize Ideas

Thought cards become a visual mind map. Ideas are clustered by theme. Drag, connect, and reorganize freely. The AI suggests connections ("This example supports that argument") and identifies gaps ("You have a strong intro and conclusion, but the middle needs more support").

### 3. Draft Mode -- Scaffolded Writing

A three-column layout designed for focused writing:

- **Left column** -- Essay scaffold with progress tracking and suggested paragraph order
- **Center column** -- The main editor with inline corrections and AI coach nudges
- **Right column** -- Corrections panel showing suggestions with explanations

Passive learning runs silently in the background. The AI builds a writing scaffold with suggested paragraph order, topic sentences, and transition phrases.

### 4. Polish Mode -- Review and Refine

The final pass before you're done:

- **Tracked changes view** -- See all suggested edits with accept/dismiss controls
- **Readability scoring** -- Understand how your writing reads
- **Structural suggestions** -- AI analyzes overall flow, argument strength, and coherence
- **Session summary** -- See what you accomplished in this writing session
- **Deep analysis** -- Uses the full power of Nemotron for style and structure suggestions

---

## Accessibility Features

The interface looks like a normal, modern word processor. **Nobody should be able to tell it's assistive software by looking at someone's screen.**

### Dyslexia-Friendly Typography

- **Specialized fonts** -- OpenDyslexic, Atkinson Hyperlegible, and Lexie Readable available as defaults
- **Minimum 16px font size** with 1.5-2.0 line spacing
- **Increased letter and word spacing** (0.05-0.12em) for easier reading

### Eye-Friendly Color Schemes

- No pure black on pure white -- uses warm dark gray on off-white/cream backgrounds
- **Multiple background tints** -- Cream, light blue, light green, and gray options
- WCAG AA contrast ratios (4.5:1 minimum for body text)
- Color is never the only indicator -- always paired with icons or text

### Two Built-In Themes

- **Cream Theme (Default)** -- Warm off-white backgrounds with dark warm text and orange accents
- **Night Theme** -- Dark blue-gray backgrounds (not pure black) with warm off-white text

### Invisible Corrections

- **Subtle colored underlines** -- Not aggressive red squiggles
- **No pop-ups or dialogs** -- Corrections appear inline
- **Focus mode** -- Dims everything except the current paragraph to reduce visual noise

### Progress Dashboard

- Shows improvement positively: "Words mastered", "Writing streak", "Ideas captured"
- **Never shows error counts** or deficit framing
- Private view -- only the user sees their own data

---

## Built with NVIDIA NIM

DysLex AI is powered by [NVIDIA NIM](https://build.nvidia.com/) inference microservices:

| Product | Model ID | Role |
|---|---|---|
| **Nemotron-3-Nano-30B-A3B** | `nvidia/nemotron-3-nano-30b-a3b` | Deep text analysis -- context-aware corrections, homophones, real-word errors, intent inference |
| **Llama 3.1 Nemotron Nano VL 8B** | `nvidia/llama-3.1-nemotron-nano-vl-8b-v1` | Vision-based idea extraction -- converts uploaded images and diagrams into thought cards |
| **MagpieTTS Multilingual** | `nvidia/magpietts` | Natural text-to-speech -- read-aloud with voices in English, Spanish, French, and more |
| **faster-whisper** | Whisper large-v3 (optimized) | Speech-to-text transcription -- real-time voice input for Capture Mode |

All cloud services are accessed through a single NVIDIA NIM API key via `https://integrate.api.nvidia.com/v1`.

## Three-Model Architecture

DysLex AI combines three models that no one has put together properly before:

| Model | Role | Runs |
|---|---|---|
| **Error Profile** | Learns each user's unique spelling/grammar patterns over time | PostgreSQL (server) |
| **Quick Correction** | Instant fixes for known errors -- no network round-trip | ONNX Runtime (browser) |
| **Deep Analysis** | Context-aware correction for homophones, real-word errors, intent inference | NVIDIA Nemotron (cloud) |

These models feed into each other through a **passive learning loop** -- the system observes natural writing behavior (self-corrections, repeated errors, word rewrites) without ever asking the user to accept or reject anything. No pop-ups. No interruptions. It just gets smarter.

### Dynamic Prompt Architecture

The LLM prompt is dynamically constructed for each user based on their error profile:

- Loads the user's top 20 most common errors
- Includes their error type breakdown and confusion pairs
- Estimates writing level from historical data
- Instructs the model to prioritize the user's known patterns
- Returns structured JSON for the frontend to display inline

---

## Design Principles

- **Voice-first, text-second.** Voice input is a first-class citizen, not an afterthought.
- **Structure emerges, not imposed.** Let ideas flow, then help organize them.
- **Corrections are invisible.** Never interrupt creative flow.
- **Show progress, not deficits.** "500 words written today" -- never "23 errors found."
- **Respect the person.** The user is intelligent. They need better tools, not simpler ideas.

---

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

**Prerequisites:** Node.js 20+, Python 3.11+, PostgreSQL 15+, Redis

### Environment Variables

```bash
# Required
NVIDIA_NIM_API_KEY=your-api-key      # For Nemotron, MagpieTTS, faster-whisper
DATABASE_URL=postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex

# Optional
VITE_API_URL=http://localhost:8000   # Backend URL for frontend
JWT_SECRET_KEY=change-me             # For authentication
```

---

## Tech Stack

**Frontend:** React 18, TipTap (ProseMirror-based editor), TypeScript (strict mode), Vite, Zustand, ONNX Runtime Web
**Backend:** Python 3.11+, FastAPI (async), SQLAlchemy 2.0 (async), Alembic, Pydantic 2.0
**Database:** PostgreSQL 15+
**ML/AI:** NVIDIA NIM (Nemotron), MagpieTTS, faster-whisper, ONNX Runtime
**Infra:** Docker Compose, Nginx

---

## Testing

DysLex AI has a full testing subsystem covering the ML models, the correction pipeline, the adaptive learning loop, the frontend UI components, and the backend API services. Tests range from hand-crafted dyslexic writing samples to unit tests for individual functions to full integration tests across the correction pipeline.

### ML model tests (dyslexic writing)

Test the ONNX and seq2seq models on realistic dyslexic writing patterns -- letter reversals, transpositions, phonetic substitutions, omissions, homophones, insertions, and severe mixed errors.

```bash
# Run the dyslexic writing test suite (39 hand-crafted samples, 8 error categories)
python ml/quick_correction/test_dyslexic.py

# With sample-level details showing every input/output
python ml/quick_correction/test_dyslexic.py --verbose

# Test only the seq2seq correction model
python ml/quick_correction/test_dyslexic.py --seq2seq-only

# Test only the ONNX error detection model
python ml/quick_correction/test_dyslexic.py --onnx-only
```

### ML benchmarks

Latency, throughput, accuracy, and memory profiling for the correction models.

```bash
# Full benchmark: latency, throughput, accuracy, memory (ONNX + PyTorch)
python ml/quick_correction/benchmark.py

# ONNX only, 200 runs
python ml/quick_correction/benchmark.py --onnx-only --runs 200

# Seq2seq evaluation on 2,400-sample test corpus
python ml/quick_correction/evaluate_seq2seq.py
```

### Frontend tests

34 test files covering UI components, services, hooks, and stores. Run the full suite or target specific areas.

```bash
cd frontend

# Run all tests
npm test

# Run a specific test file or pattern
npm test -- --testPathPattern=grammarRules
npm test -- --testPathPattern=contextRules
npm test -- --testPathPattern=correctionService

# Type checking and linting
npm run type-check
npm run lint
```

**What's covered:**

- **Correction pipeline** -- ONNX model integration, grammar rules, contextual confusion detection, correction merging, overlap removal, priority ordering, personal dictionary filtering, cloud API fallback (`correctionService.test.ts`, `onnxModel.test.ts`)
- **Grammar rules** -- Doubled words, a/an usage, capitalization after periods, subject-verb agreement, its/it's, missing punctuation (`grammarRules.test.ts`)
- **Context rules** -- their/there/they're, your/you're, to/too, then/than with position accuracy checks (`contextRules.test.ts`)
- **Stores** -- Editor state, document management, session handling, settings persistence, capture mode, mind map, polish mode, scaffold, format (`editorStore.test.ts`, `documentStore.test.ts`, `sessionStore.test.ts`, `settingsStore.test.ts`, `captureStore.test.ts`, `mindMapStore.test.ts`, `polishStore.test.ts`, `scaffoldStore.test.ts`, `formatStore.test.ts`)
- **Hooks** -- Snapshot engine for passive learning, voice input, media recording, read-aloud TTS, frustration detection (`useSnapshotEngine.test.ts`, `useVoiceInput.test.ts`, `useMediaRecorder.test.ts`, `useReadAloud.test.ts`, `useFrustrationDetector.test.ts`)
- **UI components** -- Sidebar, topbar, app layout, voice bar, font selector, dialog, toast, loading spinner, empty state, corrections panel, polish panel, settings tabs for appearance/accessibility/privacy/general (`Sidebar.test.tsx`, `Topbar.test.tsx`, `AppLayout.test.tsx`, `VoiceBar.test.tsx`, `FontSelector.test.tsx`, `CorrectionsPanel.test.tsx`, `PolishPanel.test.tsx`, etc.)
- **API client** -- Request/response handling and error cases (`api.test.ts`)

### Backend tests

22 test files covering the API endpoints, core logic, and service integrations.

```bash
cd backend

# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_adaptive_loop.py
pytest tests/test_llm_orchestrator.py
pytest tests/test_error_profile.py

# Run tests matching a keyword
pytest tests/ -k "adaptive"
pytest tests/ -k "correction"

# Type checking and linting
mypy app/ --ignore-missing-imports
ruff check app/
```

**What's covered:**

- **Adaptive learning loop** -- Tokenization, word-level diff detection, similarity scoring, Levenshtein distance, error type classification, letter reversal detection, phonetic similarity, homophone detection, omission/addition detection, snapshot pair processing (`test_adaptive_loop.py`)
- **LLM orchestrator** -- Two-tier routing logic, deep analysis triggering, correction merging, quick-only and deep-only modes, auto-routing, document review (`test_llm_orchestrator.py`)
- **Error profiles** -- User error pattern storage and retrieval (`test_error_profile.py`)
- **Corrections API** -- Endpoint request/response handling (`test_corrections.py`)
- **Quick correction** -- Model integration and error logging (`test_quick_correction.py`)
- **Repositories** -- Database CRUD operations and error handling (`test_repositories.py`, `test_repository_errors.py`)
- **Prompt builder** -- Dynamic prompt construction with user error profiles (`test_prompt_builder.py`)
- **LLM tools** -- Tool calling and function integration (`test_llm_tools.py`)
- **NIM client** -- NVIDIA NIM API integration (`test_nemotron_client.py`)
- **Voice system** -- Speech-to-text service, idea extraction, capture prompts (`test_voice_system.py`, `test_idea_extraction_service.py`, `test_capture_prompts.py`)
- **Vision** -- Image-to-thought-card extraction and prompt construction (`test_vision_extraction_service.py`, `test_vision_prompts.py`)
- **TTS** -- Text-to-speech service integration (`test_tts_service.py`)
- **User settings and privacy** -- Settings persistence and privacy endpoint handling (`test_user_settings.py`, `test_privacy_endpoints.py`)
- **Progress tracking** -- Dashboard data repository (`test_progress_repo.py`)
- **Seed data** -- Database initialization (`test_seed_data.py`)

### Latest results

The ONNX error detection model catches **94.6% of dyslexic errors** at 2.6ms with zero false positives on clean text. The seq2seq correction model fixes **42.5% of errors** on its own, with the remaining hard cases (homophones, severe mixed errors) routed to the Tier 2 Nemotron LLM. Full results: [Dyslexic Test Results](docs/dyslexic-test-results.md) | [Benchmark vs Grammarly](docs/benchmark-dyslex-vs-grammarly.md)

---

## Documentation

- [Architecture](docs/architecture.md) -- System design overview
- [API Reference](docs/api-reference.md) -- Endpoint documentation
- [Database Schema](docs/database-schema.md) -- ERD and table docs
- [ML Models](docs/ml-models.md) -- Model architecture and training
- [Dyslexic Test Results](docs/dyslexic-test-results.md) -- Model accuracy on dyslexic writing
- [Benchmark vs Grammarly](docs/benchmark-dyslex-vs-grammarly.md) -- Head-to-head comparison
- [Deployment](docs/deployment.md) -- Production setup
- [Contributing](docs/contributing.md) -- How to get involved
- [run.py Guide](RUN_PY_GUIDE.md) -- Launcher documentation

---

## License

Apache 2.0 -- See [LICENSE](LICENSE)

Dyslexia affects roughly 1 in 5 people worldwide. A tool this powerful should not be locked behind a paywall. Schools, nonprofits, and individual developers can run it, fork it, translate it, and improve it.

---

*"Everyone has ideas worth sharing. The right tool just makes sharing them easier."*

<!--
4D 61 64 65 20 42 79 20 43 6F 6E 6E 6F 72 20 53 65 63 72 69 73 74 20 46 6F 72 20 4E 76 69 64 69 61 20 47 54 43
-->
