import { useCallback, useState } from 'react';
import { useReactFlow } from '@xyflow/react';
import { useMindMapStore } from '../../../stores/mindMapStore';

interface MindMapToolbarProps {
  onBuildScaffold: () => void;
  isScaffoldLoading: boolean;
  onExtractFromText: (text: string) => Promise<void>;
}

export function MindMapToolbar({ onBuildScaffold, isScaffoldLoading, onExtractFromText }: MindMapToolbarProps) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const { addNode, nodes } = useMindMapStore();

  const [showTextInput, setShowTextInput] = useState(false);
  const [extractText, setExtractText] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);

  const handleAddIdea = useCallback(() => {
    addNode(null, {
      x: Math.random() * 400 + 100,
      y: Math.random() * 300 + 100,
    });
  }, [addNode]);

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
            onClick={() => setShowTextInput((v) => !v)}
            className={`toolbar-btn${showTextInput ? ' toolbar-btn-active' : ''}`}
            aria-label="Extract ideas from text"
            aria-expanded={showTextInput}
          >
            Extract from Text
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
    </div>
  );
}
