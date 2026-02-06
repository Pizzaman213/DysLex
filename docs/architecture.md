# DysLex AI Architecture

## System Overview

DysLex AI uses a three-model architecture for intelligent, adaptive writing assistance:

1. **Error Profile Model** (PostgreSQL) - Stores user-specific error patterns
2. **Quick Correction Model** (ONNX) - Local, fast corrections for common errors
3. **Deep Analysis Model** (Nemotron via NIM) - Cloud-based deep analysis

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   TipTap     │  │    ONNX      │  │   Passive Learning   │   │
│  │   Editor     │  │   Runtime    │  │   Snapshot Engine    │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Backend                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   FastAPI    │  │     LLM      │  │   Adaptive Loop      │   │
│  │   Routes     │  │ Orchestrator │  │   Processor          │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
│    PostgreSQL    │  │  NVIDIA NIM  │  │  NVIDIA NIM  │
│  Error Profiles  │  │   Nemotron   │  │  MagpieTTS   │
└──────────────────┘  └──────────────┘  └──────────────┘
```

## Data Flow

### Writing Flow
1. User types in TipTap editor
2. Quick Correction Model (ONNX) runs locally for instant feedback
3. On pause, text is sent to backend for deep analysis
4. Corrections appear inline (no popups)
5. User behavior tracked for passive learning

### Passive Learning Flow
1. Snapshots taken every 5-10 seconds
2. Diff computed between snapshots
3. User self-corrections detected
4. Error Profile updated automatically
5. Future corrections personalized

## Key Components

### Frontend
- **Editor**: TipTap-based rich text editor
- **Writing Modes**: Capture, Mind Map, Draft, Polish
- **ONNX Runtime**: Browser-based inference for Quick Correction Model
- **Snapshot Engine**: Tracks text changes for passive learning

### Backend
- **LLM Orchestrator**: Routes between quick and deep analysis
- **Error Profile**: User-specific pattern storage
- **Adaptive Loop**: Processes learning signals

### External Services
- **NVIDIA NIM**: Nemotron for deep analysis, MagpieTTS for TTS
- **faster-whisper**: Speech-to-text
