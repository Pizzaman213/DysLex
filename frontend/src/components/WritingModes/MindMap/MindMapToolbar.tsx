import { useCallback, useState } from 'react';
import { useReactFlow } from '@xyflow/react';
import { useMindMapStore } from '../../../stores/mindMapStore';
import { VisionCapturePanel } from '../../Shared/VisionCapturePanel';

interface MindMapToolbarProps {
  onBuildScaffold: () => void;
  isScaffoldLoading: boolean;
  onExtractFromText: (text: string) => Promise<void>;
  onExtractFromImage: (base64: string, mimeType: string) => Promise<void>;
  onTidyUp: () => void;
}

export function MindMapToolbar({ onBuildScaffold, isScaffoldLoading, onExtractFromText, onExtractFromImage, onTidyUp }: MindMapToolbarProps) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const { addNode, nodes, undo, redo, canUndo, canRedo } = useMindMapStore();

  const [showTextInput, setShowTextInput] = useState(false);
  const [showVisionCapture, setShowVisionCapture] = useState(false);
  const [extractText, setExtractText] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [isVisionProcessing, setIsVisionProcessing] = useState(false);

  const handleAddIdea = useCallback(() => {
    // Connect new nodes to the root so everything surrounds the main idea
    const rootNode = nodes.find((n) => n.id === 'root');
    const rootX = rootNode?.position.x ?? 400;
    const rootY = rootNode?.position.y ?? 200;
    const angle = Math.random() * 2 * Math.PI;
    const radius = 300 + Math.random() * 100;
    addNode('root', {
      x: rootX + Math.cos(angle) * radius,
      y: rootY + Math.sin(angle) * radius,
    });
  }, [addNode, nodes]);

  const handleZoomIn = useCallback(() => {
    zoomIn({ duration: 300 });
  }, [zoomIn]);

  const handleZoomOut = useCallback(() => {
    zoomOut({ duration: 300 });
  }, [zoomOut]);

  const handleFitView = useCallback(() => {
    fitView({ duration: 300, padding: 0.2 });
  }, [fitView]);

  const handleExtract = useCallback(async () => {
    if (!extractText.trim()) return;
    setIsExtracting(true);
    try {
      await onExtractFromText(extractText.trim());
      setExtractText('');
      setShowTextInput(false);
    } finally {
      setIsExtracting(false);
    }
  }, [extractText, onExtractFromText]);

  const handleVisionCapture = useCallback(async (base64: string, mimeType: string) => {
    setIsVisionProcessing(true);
    try {
      await onExtractFromImage(base64, mimeType);
      setShowVisionCapture(false);
    } finally {
      setIsVisionProcessing(false);
    }
  }, [onExtractFromImage]);

  const canBuildScaffold = nodes.length >= 2 && !isScaffoldLoading;

  return (
    <div className="mindmap-toolbar-wrapper">
      <div className="mindmap-toolbar" role="toolbar" aria-label="Mind map tools">
        <div className="toolbar-group">
          <button
            type="button"
            onClick={handleAddIdea}
            className="toolbar-btn"
            aria-label="Add new idea"
          >
            + Add Idea
          </button>
          <button
            type="button"
            onClick={() => { setShowTextInput((v) => !v); setShowVisionCapture(false); }}
            className={`toolbar-btn${showTextInput ? ' toolbar-btn-active' : ''}`}
            aria-label="Extract ideas from text"
            aria-expanded={showTextInput}
          >
            Extract from Text
          </button>
          <button
            type="button"
            onClick={() => { setShowVisionCapture((v) => !v); setShowTextInput(false); }}
            className={`toolbar-btn${showVisionCapture ? ' toolbar-btn-active' : ''}`}
            aria-label="Extract ideas from image"
            aria-expanded={showVisionCapture}
          >
            Scan Image
          </button>
          <button
            type="button"
            onClick={onTidyUp}
            className="toolbar-btn"
            aria-label="Auto-arrange nodes"
            title="Tidy Up"
            disabled={nodes.length <= 1}
          >
            Tidy Up
          </button>
        </div>

        <div className="toolbar-group">
          <button
            type="button"
            onClick={undo}
            className="toolbar-btn toolbar-btn-icon"
            aria-label="Undo"
            title="Undo (Cmd+Z)"
            disabled={!canUndo()}
          >
            ↶
          </button>
          <button
            type="button"
            onClick={redo}
            className="toolbar-btn toolbar-btn-icon"
            aria-label="Redo"
            title="Redo (Cmd+Shift+Z)"
            disabled={!canRedo()}
          >
            ↷
          </button>
        </div>

        <div className="toolbar-group">
          <button
            type="button"
            onClick={handleZoomIn}
            className="toolbar-btn toolbar-btn-icon"
            aria-label="Zoom in"
            title="Zoom in"
          >
            +
          </button>
          <button
            type="button"
            onClick={handleZoomOut}
            className="toolbar-btn toolbar-btn-icon"
            aria-label="Zoom out"
            title="Zoom out"
          >
            −
          </button>
          <button
            type="button"
            onClick={handleFitView}
            className="toolbar-btn toolbar-btn-icon"
            aria-label="Fit to view"
            title="Fit to view"
          >
            ⊡
          </button>
        </div>

        <div className="toolbar-group">
          <button
            type="button"
            onClick={onBuildScaffold}
            className="toolbar-btn toolbar-btn-primary"
            disabled={!canBuildScaffold}
            aria-label="Build writing scaffold"
          >
            {isScaffoldLoading ? 'Building...' : 'Build Scaffold'}
          </button>
        </div>
      </div>

      {showTextInput && (
        <div className="extract-panel">
          <textarea
            className="extract-textarea"
            value={extractText}
            onChange={(e) => setExtractText(e.target.value)}
            placeholder="Paste or type text here to extract ideas..."
            rows={4}
            disabled={isExtracting}
          />
          <div className="extract-actions">
            <button
              type="button"
              className="toolbar-btn toolbar-btn-primary"
              onClick={handleExtract}
              disabled={isExtracting || !extractText.trim()}
            >
              {isExtracting ? 'Extracting...' : 'Extract Ideas'}
            </button>
            <button
              type="button"
              className="toolbar-btn"
              onClick={() => { setShowTextInput(false); setExtractText(''); }}
              disabled={isExtracting}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {showVisionCapture && (
        <VisionCapturePanel
          onCapture={handleVisionCapture}
          isProcessing={isVisionProcessing}
          onCancel={() => setShowVisionCapture(false)}
        />
      )}
    </div>
  );
}
