# Mind Map Mode — Organize Ideas

## Purpose

Visual mind map editor for organizing ideas from capture cards. Uses React Flow for a canvas-based node/edge graph with AI-powered suggestions.

## User Experience

1. Thought cards from Capture Mode appear as nodes in circular layout
2. Central root node with topic derived from card titles
3. User drags nodes, draws connections
4. AI suggests connections and cluster names
5. Scaffold builder generates section structure for Draft Mode
6. Voice input for quick idea addition directly on canvas

## Technical Implementation

### Frontend Component

`frontend/src/components/WritingModes/MindMapMode.tsx`:
- **React Flow** canvas for drag/connect/zoom/pan
- Circular auto-positioning of capture cards (radial layout around root)
- Sub-idea nested positioning (170px radius from parent)
- Voice input button for quick node creation
- AI suggestions panel (connections, relationships)
- Scaffold builder for draft transition
- Duplicate card detection

### State Management

`frontend/src/stores/mindMapStore.ts` (Zustand with persistence):

**Node/Edge CRUD:**
- `addNode()`, `updateNodeData()`, `updateNodePosition()`, `deleteNode()`
- `addEdge()`, `updateEdgeData()`, `deleteEdge()`
- `quickAddNode()` — Creates node from voice transcript

**Advanced Features:**
- Undo/redo history (max 50 snapshots via `pushSnapshot()`)
- 5 color clusters with customizable names
- AI suggestions (`setSuggestions()`, `acceptSuggestion()`, `dismissSuggestion()`)
- Scaffold generation (`setScaffold()`)
- Orphan repair (`repairOrphans()` — ensures root exists, reconnects orphans)
- Per-document sessions (survives document switches)
- Edge handle recomputation based on relative node positions (`pickHandles()`)

### AI Suggestions

Calls `api.suggestConnections()` to get AI-generated:
- Connection suggestions between related nodes
- Cluster name suggestions
- Gap identification

### Scaffold Builder

`api.buildScaffold()` converts the mind map into a writing scaffold for Draft Mode:
- Analyzes node connections to determine section order
- Groups by cluster
- Generates section headers with topic sentences

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/WritingModes/MindMapMode.tsx` | Main component with React Flow |
| `frontend/src/stores/mindMapStore.ts` | Zustand store with undo/redo, per-document |
| `frontend/src/stores/captureStore.ts` | Source of thought cards |

## Integration Points

- [Capture Mode](capture-mode.md): Imports thought cards as nodes
- [Draft Mode](draft-mode.md): Exports scaffold structure
- [User-Scoped Storage](../frontend/user-scoped-storage.md): Per-user persistence

## Status

- [x] React Flow canvas with drag/connect/zoom
- [x] Circular layout from capture cards
- [x] Voice input for quick node addition
- [x] AI suggestions panel
- [x] Scaffold builder for draft transition
- [x] Undo/redo history
- [x] 5-cluster color coding
- [x] Per-document persistence
- [x] Orphan repair
- [ ] Full keyboard-only navigation
