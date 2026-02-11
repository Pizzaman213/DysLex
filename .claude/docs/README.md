# DysLex AI — Documentation Hub

Read the relevant doc **before** implementing or modifying any feature. See [CLAUDE.md](../../CLAUDE.md) for high-level architecture and philosophy.

## Quick Reference

### Core Architecture
| Doc | Key Files | Status |
|-----|-----------|--------|
| [Three-Model Architecture](core/three-model-architecture.md) | `llm_orchestrator.py`, `nim_client.py`, `nemotron_client.py`, `onnxModel.ts` | Implemented |
| [Adaptive Learning Loop](core/adaptive-learning-loop.md) | `adaptive_loop.py`, `scheduler.py`, `redis_client.py` | Implemented |
| [Error Profile System](core/error-profile-system.md) | `error_profile.py`, `user_error_pattern_repo.py`, `prompt_builder.py` | Implemented |
| [Circuit Breaker](core/circuit-breaker.md) | `circuit_breaker.py`, `nemotron_client.py` | Implemented |

### Writing Modes
| Doc | Key Files | Status |
|-----|-----------|--------|
| [Capture Mode](modes/capture-mode.md) | `CaptureMode.tsx`, `useVoiceInput.ts`, `captureStore.ts` | Implemented |
| [Mind Map Mode](modes/mindmap-mode.md) | `MindMapMode.tsx`, `mindMapStore.ts` (React Flow) | Implemented |
| [Draft Mode](modes/draft-mode.md) | `DraftMode.tsx`, `CorrectionsPanel.tsx`, `CoachPanel.tsx` | Implemented |
| [Polish Mode](modes/polish-mode.md) | `PolishMode.tsx`, `useReadAloud.ts`, `useTtsPrewarmer.ts` | Partial |
| [Brainstorm Mode](modes/brainstorm-mode.md) | `useBrainstormLoop.ts`, `brainstorm_service.py` | Implemented |

### Frontend
| Doc | Key Files | Status |
|-----|-----------|--------|
| [TipTap Editor](frontend/tiptap-editor.md) | `Editor.tsx`, `DraftMode.tsx` (DyslexEditor), `CoachPanel.tsx` | Implemented |
| [Correction Overlay](frontend/correction-overlay.md) | `CorrectionOverlay.tsx`, `CorrectionsPanel.tsx` | Implemented |
| [Themes](frontend/themes.md) | `tokens.css`, `cream.css`, `night.css` | Implemented |
| [Accessibility](frontend/accessibility.md) | `tokens.css`, `global.css` | Partial |
| [Progress Dashboard](frontend/progress-dashboard.md) | `progress_repo.py` (backend queries ready) | Backend only |
| [Frustration Detection](frontend/frustration-detection.md) | `useFrustrationDetector.ts` | Implemented |
| [User-Scoped Storage](frontend/user-scoped-storage.md) | `userScopedStorage.ts`, `captureStore.ts`, `mindMapStore.ts` | Implemented |
| [ONNX Local Correction](frontend/onnx-local-correction.md) | `onnxModel.ts`, `quick_correction_service.py` | Implemented |

### Backend
| Doc | Key Files | Status |
|-----|-----------|--------|
| [LLM Orchestrator](backend/llm-orchestrator.md) | `llm_orchestrator.py`, `prompt_builder.py` | Implemented |
| [NIM Integration](backend/nim-integration.md) | `nemotron_client.py`, `tts_service.py`, `grpc_tts_client.py` | Implemented |
| [Database Schema](backend/database-schema.md) | `models.py`, `alembic/versions/` (001-008) | Implemented |
| [Passkey Authentication](backend/passkey-authentication.md) | `passkey.py`, `auth.py` | Implemented |
| [Background Scheduler](backend/background-scheduler.md) | `scheduler.py` (5 jobs) | Implemented |
| [Redis Caching Layer](backend/redis-caching-layer.md) | `redis_client.py` | Implemented |
| [Snapshot Engine](backend/snapshot-engine.md) | `adaptive_loop.py`, `redis_client.py` | Implemented |
| [Voice Input](backend/voice-input.md) | `useVoiceInput.ts` (browser-only, no backend STT) | Implemented |
| [Text-to-Speech](backend/text-to-speech.md) | `tts_service.py`, `grpc_tts_client.py`, `useReadAloud.ts` | Implemented |

## Which Docs to Read First

**Adding a new writing mode?** Start with [Three-Model Architecture](core/three-model-architecture.md), then the existing mode closest to yours.

**Working on corrections?** Read [LLM Orchestrator](backend/llm-orchestrator.md) → [ONNX Local Correction](frontend/onnx-local-correction.md) → [Correction Overlay](frontend/correction-overlay.md).

**Working on the learning loop?** Read [Adaptive Learning Loop](core/adaptive-learning-loop.md) → [Error Profile](core/error-profile-system.md) → [Background Scheduler](backend/background-scheduler.md).

**Working on voice/TTS?** Read [Voice Input](backend/voice-input.md) → [Text-to-Speech](backend/text-to-speech.md) → [Brainstorm Mode](modes/brainstorm-mode.md).

**Working on auth?** Read [Passkey Authentication](backend/passkey-authentication.md) → [User-Scoped Storage](frontend/user-scoped-storage.md).

**Working on database?** Read [Database Schema](backend/database-schema.md) → [Error Profile](core/error-profile-system.md).
