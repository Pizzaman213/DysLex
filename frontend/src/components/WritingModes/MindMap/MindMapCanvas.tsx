import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Connection,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useMindMapStore } from '../../../stores/mindMapStore';
import { MindMapNode } from './MindMapNode';
import { MindMapEdge } from './MindMapEdge';
import { MindMapToolbar } from './MindMapToolbar';

interface MindMapCanvasInnerProps {
  onBuildScaffold: () => void;
  isScaffoldLoading: boolean;
  onExtractFromText: (text: string) => Promise<void>;
}

function MindMapCanvasInner({ onBuildScaffold, isScaffoldLoading, onExtractFromText }: MindMapCanvasInnerProps) {
  const {
    nodes: storeNodes,
    edges: storeEdges,
    addEdge: storeAddEdge,
    updateNodePosition,
  } = useMindMapStore();

  // No need for separate state - we use store directly

  const nodeTypes = useMemo(
    () => ({
      mindMapNode: MindMapNode,
    }),
    []
  );

  const edgeTypes = useMemo(
    () => ({
      default: MindMapEdge,
    }),
    []
  );

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const updatedNodes = applyNodeChanges(changes, storeNodes) as typeof storeNodes;
      useMindMapStore.setState({ nodes: updatedNodes });

      // Update positions in store
      changes.forEach((change) => {
        if (change.type === 'position' && change.position && !change.dragging) {
          updateNodePosition(change.id, change.position);
        }
      });
    },
    [storeNodes, updateNodePosition]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const updatedEdges = applyEdgeChanges(changes, storeEdges) as typeof storeEdges;
      useMindMapStore.setState({ edges: updatedEdges });
    },
    [storeEdges]
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target) {
        storeAddEdge(connection.source, connection.target);
      }
    },
    [storeAddEdge]
  );

  const getNodeColor = useCallback((node: any) => {
    const cluster = node.data?.cluster || 1;
    return `var(--color-cluster-${cluster})`;
  }, []);

  return (
    <div className="mindmap-canvas-container">
      <MindMapToolbar onBuildScaffold={onBuildScaffold} isScaffoldLoading={isScaffoldLoading} onExtractFromText={onExtractFromText} />
      <ReactFlow
        nodes={storeNodes}
        edges={storeEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        minZoom={0.25}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        className="mindmap-reactflow"
      >
        <Background gap={16} size={1} color="var(--color-border)" />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={getNodeColor}
          maskColor="var(--bg-primary)"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--color-border)',
          }}
        />
      </ReactFlow>
    </div>
  );
}

interface MindMapCanvasProps {
  onBuildScaffold: () => void;
  isScaffoldLoading: boolean;
  onExtractFromText: (text: string) => Promise<void>;
}

export function MindMapCanvas({ onBuildScaffold, isScaffoldLoading, onExtractFromText }: MindMapCanvasProps) {
  return (
    <ReactFlowProvider>
      <MindMapCanvasInner onBuildScaffold={onBuildScaffold} isScaffoldLoading={isScaffoldLoading} onExtractFromText={onExtractFromText} />
    </ReactFlowProvider>
  );
}
