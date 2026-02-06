import { useState, useCallback } from 'react';

interface Node {
  id: string;
  text: string;
  x: number;
  y: number;
  connections: string[];
}

interface MindMapModeProps {
  onExport: (nodes: Node[]) => void;
}

export function MindMapMode({ onExport }: MindMapModeProps) {
  const [nodes, setNodes] = useState<Node[]>([
    { id: 'root', text: 'Main Idea', x: 300, y: 200, connections: [] },
  ]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const addNode = useCallback((parentId: string) => {
    const parent = nodes.find((n) => n.id === parentId);
    if (!parent) return;

    const newNode: Node = {
      id: `node-${Date.now()}`,
      text: 'New idea',
      x: parent.x + 150,
      y: parent.y + Math.random() * 100 - 50,
      connections: [],
    };

    setNodes((prev) => [
      ...prev.map((n) =>
        n.id === parentId
          ? { ...n, connections: [...n.connections, newNode.id] }
          : n
      ),
      newNode,
    ]);
  }, [nodes]);

  const updateNodeText = useCallback((id: string, text: string) => {
    setNodes((prev) =>
      prev.map((n) => (n.id === id ? { ...n, text } : n))
    );
  }, []);

  return (
    <div className="mindmap-mode" role="application" aria-label="Mind map canvas">
      <div className="mindmap-toolbar">
        <button
          onClick={() => selectedNode && addNode(selectedNode)}
          disabled={!selectedNode}
          aria-label="Add connected idea"
        >
          Add Branch
        </button>
        <button
          onClick={() => onExport(nodes)}
          aria-label="Export to draft"
        >
          Export to Draft
        </button>
      </div>

      <svg className="mindmap-canvas" viewBox="0 0 600 400">
        {nodes.map((node) =>
          node.connections.map((connId) => {
            const target = nodes.find((n) => n.id === connId);
            if (!target) return null;
            return (
              <line
                key={`${node.id}-${connId}`}
                x1={node.x}
                y1={node.y}
                x2={target.x}
                y2={target.y}
                className="mindmap-connection"
              />
            );
          })
        )}

        {nodes.map((node) => (
          <g
            key={node.id}
            transform={`translate(${node.x}, ${node.y})`}
            onClick={() => setSelectedNode(node.id)}
            role="button"
            tabIndex={0}
            aria-label={`Node: ${node.text}`}
            aria-selected={selectedNode === node.id}
          >
            <circle
              r="30"
              className={`mindmap-node ${selectedNode === node.id ? 'selected' : ''}`}
            />
            <foreignObject x="-25" y="-10" width="50" height="20">
              <input
                type="text"
                value={node.text}
                onChange={(e) => updateNodeText(node.id, e.target.value)}
                className="mindmap-node-text"
                aria-label="Edit node text"
              />
            </foreignObject>
          </g>
        ))}
      </svg>
    </div>
  );
}
