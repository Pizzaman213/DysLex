import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Connection,
  ConnectionMode,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useMindMapStore } from '../../../stores/mindMapStore';
import { MindMapNode } from './MindMapNode';
import { MindMapEdge } from './MindMapEdge';
import { MindMapToolbar } from './MindMapToolbar';
import { EdgeLabelPicker } from './EdgeLabelPicker';
import { EdgeRelationship } from './types';
import { computeAutoLayout } from './autoLayout';

interface LabelPickerState {
  edgeId: string;
  position: { x: number; y: number };
  isNew: boolean; // true when just created via onConnect
}

interface MindMapCanvasInnerProps {
  onBuildScaffold: () => void;
  isScaffoldLoading: boolean;
  onExtractFromText: (text: string) => Promise<void>;
  onExtractFromImage: (base64: string, mimeType: string) => Promise<void>;
  viewportCenterRef?: React.MutableRefObject<() => { x: number; y: number }>;
}

function MindMapCanvasInner({
  onBuildScaffold,
  isScaffoldLoading,
  onExtractFromText,
  onExtractFromImage,
  viewportCenterRef,
}: MindMapCanvasInnerProps) {
  const {
    nodes: storeNodes,
    edges: storeEdges,
    addEdge: storeAddEdge,
    updateEdgeData,
    updateNodePosition,
    pushSnapshot,
    undo,
    redo,
    setNodePositions,
    refreshEdgeHandles,
  } = useMindMapStore();

  const { screenToFlowPosition } = useReactFlow();

  // Expose viewport center to parent
  useEffect(() => {
    if (viewportCenterRef) {
      viewportCenterRef.current = () => {
        return screenToFlowPosition({
          x: window.innerWidth / 2,
          y: window.innerHeight / 2,
        });
      };
    }
  }, [viewportCenterRef, screenToFlowPosition]);

  const [labelPicker, setLabelPicker] = useState<LabelPickerState | null>(null);

  // Track whether a drag is in progress to push snapshot on drag-start
  const isDraggingRef = useRef(false);

  // Animation ref for tidy-up
  const isAnimatingRef = useRef(false);
  const animationFrameRef = useRef<number>(0);

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
      // Push snapshot when drag starts
      changes.forEach((change) => {
        if (change.type === 'position' && change.dragging && !isDraggingRef.current) {
          isDraggingRef.current = true;
          // Cancel any running animation
          if (isAnimatingRef.current) {
            cancelAnimationFrame(animationFrameRef.current);
            isAnimatingRef.current = false;
          }
          pushSnapshot();
        }
        if (change.type === 'position' && !change.dragging && isDraggingRef.current) {
          isDraggingRef.current = false;
          // Recompute edge handles after drag settles
          requestAnimationFrame(() => refreshEdgeHandles());
        }
      });

      const updatedNodes = applyNodeChanges(changes, storeNodes) as typeof storeNodes;
      useMindMapStore.setState({ nodes: updatedNodes });

      changes.forEach((change) => {
        if (change.type === 'position' && change.position && !change.dragging) {
          updateNodePosition(change.id, change.position);
        }
      });
    },
    [storeNodes, updateNodePosition, pushSnapshot, refreshEdgeHandles]
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
        // Show label picker at midpoint between source and target
        const sourceNode = storeNodes.find((n) => n.id === connection.source);
        const targetNode = storeNodes.find((n) => n.id === connection.target);
        if (sourceNode && targetNode) {
          const midX = (sourceNode.position.x + targetNode.position.x) / 2;
          const midY = (sourceNode.position.y + targetNode.position.y) / 2;
          const edgeId = `edge-${connection.source}-${connection.target}`;
          setLabelPicker({ edgeId, position: { x: midX, y: midY }, isNew: true });
        }
      }
    },
    [storeAddEdge, storeNodes]
  );

  const onEdgeDoubleClick = useCallback(
    (_event: React.MouseEvent, edge: any) => {
      const sourceNode = storeNodes.find((n) => n.id === edge.source);
      const targetNode = storeNodes.find((n) => n.id === edge.target);
      if (sourceNode && targetNode) {
        const midX = (sourceNode.position.x + targetNode.position.x) / 2;
        const midY = (sourceNode.position.y + targetNode.position.y) / 2;
        setLabelPicker({ edgeId: edge.id, position: { x: midX, y: midY }, isNew: false });
      }
    },
    [storeNodes]
  );

  const handleLabelSelect = useCallback(
    (relationship: EdgeRelationship | null) => {
      if (labelPicker) {
        updateEdgeData(labelPicker.edgeId, { relationship });
        setLabelPicker(null);
      }
    },
    [labelPicker, updateEdgeData]
  );

  const handleLabelPickerClose = useCallback(() => {
    setLabelPicker(null);
  }, []);

  // Keyboard shortcuts for undo/redo
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip if focused on an input/textarea element
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) {
        return;
      }

      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if (isMeta && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        redo();
      } else if (isMeta && e.key === 'y') {
        e.preventDefault();
        redo();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo]);

  // Auto-layout: animate to target positions
  const handleTidyUp = useCallback(() => {
    if (storeNodes.length <= 1) return;

    const targetPositions = computeAutoLayout(storeNodes, storeEdges);

    // Check prefers-reduced-motion
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReduced) {
      setNodePositions(targetPositions);
      return;
    }

    // Animate over 500ms with ease-out cubic
    const startPositions = new Map(
      storeNodes.map((n) => [n.id, { x: n.position.x, y: n.position.y }])
    );

    pushSnapshot();
    isAnimatingRef.current = true;
    const startTime = performance.now();
    const duration = 500;

    const animate = (now: number) => {
      if (!isAnimatingRef.current) return;

      const elapsed = now - startTime;
      const rawT = Math.min(elapsed / duration, 1);
      // Ease-out cubic: 1 - (1 - t)^3
      const t = 1 - Math.pow(1 - rawT, 3);

      const interpolated = new Map<string, { x: number; y: number }>();
      for (const [id, target] of targetPositions) {
        const start = startPositions.get(id);
        if (start) {
          interpolated.set(id, {
            x: start.x + (target.x - start.x) * t,
            y: start.y + (target.y - start.y) * t,
          });
        }
      }

      // Direct state update (no history — snapshot already pushed)
      const currentNodes = useMindMapStore.getState().nodes;
      useMindMapStore.setState({
        nodes: currentNodes.map((node) => {
          const pos = interpolated.get(node.id);
          return pos ? { ...node, position: pos } : node;
        }),
      });

      if (rawT < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        isAnimatingRef.current = false;
        refreshEdgeHandles();
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);
  }, [storeNodes, storeEdges, setNodePositions, pushSnapshot, refreshEdgeHandles]);

  // Cleanup animation on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const getNodeColor = useCallback((node: any) => {
    const cluster = node.data?.cluster || 1;
    return `var(--color-cluster-${cluster})`;
  }, []);

  return (
    <div className="mindmap-canvas-container">
      <MindMapToolbar
        onBuildScaffold={onBuildScaffold}
        isScaffoldLoading={isScaffoldLoading}
        onExtractFromText={onExtractFromText}
        onExtractFromImage={onExtractFromImage}
        onTidyUp={handleTidyUp}
      />
      <ReactFlow
        nodes={storeNodes}
        edges={storeEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onEdgeDoubleClick={onEdgeDoubleClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        connectionMode={ConnectionMode.Loose}
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
      {labelPicker && (
        <EdgeLabelPicker
          position={labelPicker.position}
          currentRelationship={
            storeEdges.find((e) => e.id === labelPicker.edgeId)?.data?.relationship ?? null
          }
          onSelect={handleLabelSelect}
          onClose={handleLabelPickerClose}
        />
      )}
    </div>
  );
}

interface MindMapCanvasProps {
  onBuildScaffold: () => void;
  isScaffoldLoading: boolean;
  onExtractFromText: (text: string) => Promise<void>;
  onExtractFromImage: (base64: string, mimeType: string) => Promise<void>;
  viewportCenterRef?: React.MutableRefObject<() => { x: number; y: number }>;
}

export function MindMapCanvas({
  onBuildScaffold,
  isScaffoldLoading,
  onExtractFromText,
  onExtractFromImage,
  viewportCenterRef,
}: MindMapCanvasProps) {
  return (
    <ReactFlowProvider>
      <MindMapCanvasInner
        onBuildScaffold={onBuildScaffold}
        isScaffoldLoading={isScaffoldLoading}
        onExtractFromText={onExtractFromText}
        onExtractFromImage={onExtractFromImage}
        viewportCenterRef={viewportCenterRef}
      />
    </ReactFlowProvider>
  );
}
