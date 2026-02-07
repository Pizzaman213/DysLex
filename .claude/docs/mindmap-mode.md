# Mind Map Mode — Organize Ideas

## Purpose

Mind Map Mode provides visual organization for scattered thoughts. Dyslexic thinkers often have many ideas but struggle to structure them linearly. This mode lets them see all ideas at once and drag them into logical groups.

**Key insight**: Don't force linear outlining. Let structure emerge from visual arrangement.

## User Experience

1. Thought cards from Capture Mode (or new ideas) appear as nodes
2. User drags nodes to arrange spatially
3. User draws connections between related ideas
4. AI suggests connections: "This example supports that argument"
5. AI identifies gaps: "You have intro and conclusion, but middle needs support"
6. User exports structure to Draft Mode

### What Users See
- Canvas with draggable idea nodes
- Lines connecting related nodes
- Color coding by theme/cluster
- AI suggestions appearing subtly
- "Export to Draft" button

### What Users Don't See
- Graph algorithms
- Clustering logic
- Suggestion generation

## Technical Implementation

### Frontend Component

```typescript
// frontend/src/components/WritingModes/MindMapMode.tsx
interface Node {
  id: string;
  text: string;
  x: number;
  y: number;
  connections: string[];
}

export function MindMapMode({ onExport }: MindMapModeProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const addNode = useCallback((parentId: string) => {
    // Create new node connected to parent
  }, []);

  const updateNodeText = useCallback((id: string, text: string) => {
    // Update node content
  }, []);

  return (
    <div className="mindmap-mode">
      <svg className="mindmap-canvas">
        {/* Render connections */}
        {/* Render nodes */}
      </svg>
    </div>
  );
}
```

### Node Data Structure

```typescript
interface MindMapNode {
  id: string;
  text: string;
  position: { x: number; y: number };
  connections: string[];  // IDs of connected nodes
  type: 'idea' | 'example' | 'argument' | 'question';
  cluster?: string;  // AI-assigned cluster
}

interface MindMapState {
  nodes: MindMapNode[];
  selectedNodes: string[];
  zoom: number;
  pan: { x: number; y: number };
}
```

### AI Suggestions (Future)

```python
# backend/app/services/mindmap_analyzer.py
async def analyze_mindmap(nodes: list[Node]) -> list[Suggestion]:
    """Analyze mind map structure and suggest improvements."""
    suggestions = []

    # Check for orphan nodes (no connections)
    # Identify potential clusters
    # Suggest missing connections
    # Identify structural gaps

    return suggestions
```

## Key Files

### Frontend
- `frontend/src/components/WritingModes/MindMapMode.tsx` — Main component
- (Future) `frontend/src/components/MindMap/Node.tsx` — Individual node
- (Future) `frontend/src/components/MindMap/Connection.tsx` — Connection line

### Backend
- (Future) `backend/app/services/mindmap_analyzer.py` — AI analysis

## Canvas Implementation Options

1. **SVG** (Current): Simple, good for small maps
2. **Canvas API**: Better performance for large maps
3. **React Flow**: Full-featured library option
4. **Custom WebGL**: Maximum performance (overkill for MVP)

## Gestures & Interactions

| Action | Gesture | Keyboard |
|--------|---------|----------|
| Select node | Click | Tab to navigate |
| Move node | Drag | Arrow keys |
| Create connection | Drag from node edge | C key |
| Add child node | Double-click | Enter key |
| Delete node | Right-click menu | Delete key |
| Zoom | Scroll wheel | +/- keys |
| Pan | Drag canvas | Shift + arrows |

## Accessibility Requirements

- **Keyboard navigation**: Full control without mouse
- **Screen reader**: Nodes announced with connections
- **High contrast**: Nodes visible in all themes
- **Focus indicators**: Clear which node is selected
- **Zoom controls**: Visible buttons, not just gestures

## Integration Points

- **Capture Mode**: Imports thought cards as nodes
- **Draft Mode**: Exports structure as outline
- **AI Analysis**: Sends node graph for suggestions

## Export to Draft

When user clicks "Export to Draft":

1. Analyze node connections to determine order
2. Group nodes by cluster
3. Generate section structure
4. Create topic sentences from node text
5. Pass to Draft Mode with scaffold

## Status

- [x] Basic component structure
- [x] Node dragging implemented
- [ ] Connection drawing
- [ ] AI suggestions
- [ ] Cluster detection
- [ ] Export to Draft
- [ ] Full accessibility
