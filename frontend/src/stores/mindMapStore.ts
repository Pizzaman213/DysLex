import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { createUserScopedStorage, registerScopedStore } from '@/services/userScopedStorage'; /* scoped storage migration, connor secrist */
import {
  MindMapFlowNode,
  MindMapFlowEdge,
  MindMapNodeData,
  MindMapEdgeData,
  AISuggestion,
  EdgeRelationship,
  Scaffold,
} from '../components/WritingModes/MindMap/types';
import { resolveOverlaps } from '../components/WritingModes/MindMap/autoLayout';

interface HistorySnapshot {
  nodes: MindMapFlowNode[];
  edges: MindMapFlowEdge[];
}

const MAX_HISTORY = 50;

type ClusterNames = Record<1 | 2 | 3 | 4 | 5, string>;

const DEFAULT_CLUSTER_NAMES: ClusterNames = {
  1: 'Cluster 1',
  2: 'Cluster 2',
  3: 'Cluster 3',
  4: 'Cluster 4',
  5: 'Cluster 5',
};

/** Persisted per-document mind map data */
interface DocumentMindMapData {
  nodes: MindMapFlowNode[];
  edges: MindMapFlowEdge[];
  scaffold: Scaffold | null;
  clusterNames: ClusterNames;
}

/** Transient (in-memory only) per-document data */
interface TransientMindMapData {
  suggestions: AISuggestion[];
  isSuggestionsLoading: boolean;
  _past: HistorySnapshot[];
  _future: HistorySnapshot[];
}

interface MindMapState {
  // Working copy (active document)
  nodes: MindMapFlowNode[];
  edges: MindMapFlowEdge[];
  suggestions: AISuggestion[];
  isSuggestionsLoading: boolean;
  scaffold: Scaffold | null;
  clusterNames: ClusterNames;

  // Per-document storage
  maps: Record<string, DocumentMindMapData>;
  _transientMap: Record<string, TransientMindMapData>;
  _activeDocumentId: string | null;

  // History (undo/redo)
  _past: HistorySnapshot[];
  _future: HistorySnapshot[];
  _skipHistory: boolean;
  pushSnapshot: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;

  // Node CRUD
  addNode: (
    parentId: string | null,
    position: { x: number; y: number },
    data?: Partial<MindMapNodeData>
  ) => void;
  updateNodeData: (id: string, partial: Partial<MindMapNodeData>) => void;
  updateNodePosition: (id: string, position: { x: number; y: number }) => void;
  deleteNode: (id: string) => void;
  setNodePositions: (positions: Map<string, { x: number; y: number }>) => void;
  quickAddNode: (transcript: string, position: { x: number; y: number }) => void;

  // Edge CRUD
  addEdge: (source: string, target: string, relationship?: EdgeRelationship | null) => void;
  updateEdgeData: (id: string, partial: Partial<MindMapEdgeData>) => void;
  deleteEdge: (id: string) => void;

  // Batch helpers
  batchUpdate: (fn: () => void) => void;

  // Edge routing
  refreshEdgeHandles: () => void;

  // Suggestions
  setSuggestions: (suggestions: AISuggestion[]) => void;
  setIsSuggestionsLoading: (loading: boolean) => void;
  acceptSuggestion: (id: string) => void;
  dismissSuggestion: (id: string) => void;

  // Cluster names
  setClusterName: (cluster: 1 | 2 | 3 | 4 | 5, name: string) => void;

  // Scaffold
  setScaffold: (scaffold: Scaffold | null) => void;

  // Repair
  repairOrphans: () => void;

  // Per-document
  setActiveDocument: (docId: string) => void;
  deleteDocumentMap: (docId: string) => void;

  // Reset
  resetMindMap: () => void;
}

const defaultNode: MindMapFlowNode = {
  id: 'root',
  type: 'mindMapNode',
  position: { x: 400, y: 200 },
  data: { title: '', body: '', cluster: 1 },
};

function emptyDocumentData(): DocumentMindMapData {
  return {
    nodes: [{ ...defaultNode, data: { ...defaultNode.data } }],
    edges: [],
    scaffold: null,
    clusterNames: { ...DEFAULT_CLUSTER_NAMES },
  };
}

function emptyTransientData(): TransientMindMapData {
  return {
    suggestions: [],
    isSuggestionsLoading: false,
    _past: [],
    _future: [],
  };
}

function pushHistory(state: MindMapState): Partial<MindMapState> {
  if (state._skipHistory) return {};
  const snapshot: HistorySnapshot = {
    nodes: structuredClone(state.nodes),
    edges: structuredClone(state.edges),
  };
  const past = [...state._past, snapshot];
  if (past.length > MAX_HISTORY) past.shift();
  return { _past: past, _future: [] };
}

const CLUSTER_CYCLE: Array<1 | 2 | 3 | 4 | 5> = [1, 2, 3, 4, 5];

/**
 * Pick the best source/target handle IDs based on relative node positions.
 * Returns the pair that produces the shortest, most direct edge.
 */
function pickHandles(
  sourcePos: { x: number; y: number },
  targetPos: { x: number; y: number }
): { sourceHandle: string; targetHandle: string } {
  const dx = targetPos.x - sourcePos.x;
  const dy = targetPos.y - sourcePos.y;

  // Determine dominant axis
  if (Math.abs(dx) >= Math.abs(dy)) {
    // Horizontal dominant
    if (dx >= 0) {
      return { sourceHandle: 'source-right', targetHandle: 'target-left' };
    }
    return { sourceHandle: 'source-left', targetHandle: 'target-right' };
  }
  // Vertical dominant
  if (dy >= 0) {
    return { sourceHandle: 'source-bottom', targetHandle: 'target-top' };
  }
  return { sourceHandle: 'source-top', targetHandle: 'target-bottom' };
}

/**
 * Recompute sourceHandle/targetHandle on all edges based on current node positions.
 */
function recomputeEdgeHandles(
  nodes: MindMapFlowNode[],
  edges: MindMapFlowEdge[]
): MindMapFlowEdge[] {
  const posMap = new Map(nodes.map((n) => [n.id, n.position]));
  return edges.map((edge) => {
    const sp = posMap.get(edge.source);
    const tp = posMap.get(edge.target);
    if (!sp || !tp) return edge;
    const handles = pickHandles(sp, tp);
    return { ...edge, sourceHandle: handles.sourceHandle, targetHandle: handles.targetHandle };
  });
}

export const useMindMapStore = create<MindMapState>()(
  persist(
    (set, get) => ({
      nodes: [defaultNode],
      edges: [],
      suggestions: [],
      isSuggestionsLoading: false,
      scaffold: null,
      clusterNames: { ...DEFAULT_CLUSTER_NAMES },
      maps: {},
      _transientMap: {},
      _activeDocumentId: null,
      _past: [],
      _future: [],
      _skipHistory: false,

      pushSnapshot: () => {
        const state = get();
        const snapshot: HistorySnapshot = {
          nodes: structuredClone(state.nodes),
          edges: structuredClone(state.edges),
        };
        const past = [...state._past, snapshot];
        if (past.length > MAX_HISTORY) past.shift();
        set({ _past: past, _future: [] });
      },

      undo: () => {
        const { _past, nodes, edges } = get();
        if (_past.length === 0) return;
        const previous = _past[_past.length - 1];
        const newPast = _past.slice(0, -1);
        const currentSnapshot: HistorySnapshot = {
          nodes: structuredClone(nodes),
          edges: structuredClone(edges),
        };
        set((state) => ({
          nodes: previous.nodes,
          edges: previous.edges,
          _past: newPast,
          _future: [...state._future, currentSnapshot],
        }));
      },

      redo: () => {
        const { _future, nodes, edges } = get();
        if (_future.length === 0) return;
        const next = _future[_future.length - 1];
        const newFuture = _future.slice(0, -1);
        const currentSnapshot: HistorySnapshot = {
          nodes: structuredClone(nodes),
          edges: structuredClone(edges),
        };
        set((state) => ({
          nodes: next.nodes,
          edges: next.edges,
          _future: newFuture,
          _past: [...state._past, currentSnapshot],
        }));
      },

      canUndo: () => get()._past.length > 0,
      canRedo: () => get()._future.length > 0,

      addNode: (parentId, position, data) => {
        const newNode: MindMapFlowNode = {
          id: `node-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
          type: 'mindMapNode',
          position,
          data: {
            title: data?.title || 'New Idea',
            body: data?.body || '',
            cluster: data?.cluster || 1,
          },
        };

        set((state) => {
          // Find parent position for handle computation
          const parentNode = parentId ? state.nodes.find((n) => n.id === parentId) : null;
          const handles = parentNode ? pickHandles(parentNode.position, position) : null;

          const newEdges = parentId
            ? [{
                id: `edge-${parentId}-${newNode.id}`,
                source: parentId,
                target: newNode.id,
                data: { relationship: null },
                ...(handles ?? {}),
              }]
            : [];

          const nextNodes = [...state.nodes, newNode];
          const nextEdges = [...state.edges, ...newEdges];
          const adjusted = resolveOverlaps(nextNodes, nextEdges);
          const finalNodes = adjusted
            ? nextNodes.map((n) => {
                const pos = adjusted.get(n.id);
                return pos ? { ...n, position: pos } : n;
              })
            : nextNodes;
          return {
            ...pushHistory(state),
            nodes: finalNodes,
            // Recompute handles if overlap resolution moved nodes
            edges: adjusted ? recomputeEdgeHandles(finalNodes, nextEdges) : nextEdges,
          };
        });
      },

      updateNodeData: (id, partial) => {
        set((state) => ({
          ...pushHistory(state),
          nodes: state.nodes.map((node) =>
            node.id === id
              ? { ...node, data: { ...node.data, ...partial } }
              : node
          ),
        }));
      },

      updateNodePosition: (id, position) => {
        // No history push — called continuously during drag
        set((state) => ({
          nodes: state.nodes.map((node) =>
            node.id === id ? { ...node, position } : node
          ),
        }));
      },

      deleteNode: (id) => {
        if (id === 'root') return;

        set((state) => ({
          ...pushHistory(state),
          nodes: state.nodes.filter((node) => node.id !== id),
          edges: state.edges.filter(
            (edge) => edge.source !== id && edge.target !== id
          ),
        }));
      },

      setNodePositions: (positions) => {
        set((state) => {
          const nextNodes = state.nodes.map((node) => {
            const pos = positions.get(node.id);
            return pos ? { ...node, position: pos } : node;
          });
          return {
            ...pushHistory(state),
            nodes: nextNodes,
            edges: recomputeEdgeHandles(nextNodes, state.edges),
          };
        });
      },

      quickAddNode: (transcript, position) => {
        const title = transcript.charAt(0).toUpperCase() + transcript.slice(1);
        const truncatedTitle = title.length > 60 ? title.substring(0, 57) + '...' : title;

        // Cycle cluster color based on existing non-root node count
        const nonRootCount = get().nodes.filter((n) => n.id !== 'root').length;
        const cluster = CLUSTER_CYCLE[nonRootCount % CLUSTER_CYCLE.length];

        // Add jitter to avoid stacking
        const jitterX = (Math.random() - 0.5) * 60;
        const jitterY = (Math.random() - 0.5) * 60;

        const newNode: MindMapFlowNode = {
          id: `node-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
          type: 'mindMapNode',
          position: { x: position.x + jitterX, y: position.y + jitterY },
          data: {
            title: truncatedTitle,
            body: transcript.length > 60 ? transcript : '',
            cluster,
          },
        };

        set((state) => {
          const rootNode = state.nodes.find((n) => n.id === 'root');
          const handles = rootNode
            ? pickHandles(rootNode.position, newNode.position)
            : {};

          const newEdge = {
            id: `edge-root-${newNode.id}`,
            source: 'root',
            target: newNode.id,
            data: { relationship: null },
            ...handles,
          };

          const nextNodes = [...state.nodes, newNode];
          const nextEdges = [...state.edges, newEdge];
          const adjusted = resolveOverlaps(nextNodes, nextEdges);
          const finalNodes = adjusted
            ? nextNodes.map((n) => {
                const pos = adjusted.get(n.id);
                return pos ? { ...n, position: pos } : n;
              })
            : nextNodes;
          return {
            ...pushHistory(state),
            nodes: finalNodes,
            edges: adjusted ? recomputeEdgeHandles(finalNodes, nextEdges) : nextEdges,
          };
        });
      },

      addEdge: (source, target, relationship) => {
        const { edges, nodes } = get();
        const edgeExists = edges.some(
          (edge) => edge.source === source && edge.target === target
        );

        if (!edgeExists) {
          const sourceNode = nodes.find((n) => n.id === source);
          const targetNode = nodes.find((n) => n.id === target);
          const handles = sourceNode && targetNode
            ? pickHandles(sourceNode.position, targetNode.position)
            : {};

          const newEdge: MindMapFlowEdge = {
            id: `edge-${source}-${target}`,
            source,
            target,
            data: { relationship: relationship ?? null },
            ...handles,
          };
          set((state) => ({
            ...pushHistory(state),
            edges: [...state.edges, newEdge],
          }));
        }
      },

      updateEdgeData: (id, partial) => {
        set((state) => ({
          ...pushHistory(state),
          edges: state.edges.map((edge) =>
            edge.id === id
              ? { ...edge, data: { ...edge.data, ...partial } }
              : edge
          ),
        }));
      },

      deleteEdge: (id) => {
        set((state) => ({
          ...pushHistory(state),
          edges: state.edges.filter((edge) => edge.id !== id),
        }));
      },

      batchUpdate: (fn) => {
        const state = get();
        const snapshot: HistorySnapshot = {
          nodes: structuredClone(state.nodes),
          edges: structuredClone(state.edges),
        };
        const past = [...state._past, snapshot];
        if (past.length > MAX_HISTORY) past.shift();
        set({ _past: past, _future: [], _skipHistory: true });
        fn();
        set({ _skipHistory: false });

        // Resolve overlaps and recompute edge handles
        const afterState = get();
        const adjusted = resolveOverlaps(afterState.nodes, afterState.edges);
        const finalNodes = adjusted
          ? afterState.nodes.map((n) => {
              const pos = adjusted.get(n.id);
              return pos ? { ...n, position: pos } : n;
            })
          : afterState.nodes;
        set({
          nodes: finalNodes,
          edges: recomputeEdgeHandles(finalNodes, afterState.edges),
        });
      },

      refreshEdgeHandles: () => {
        const { nodes: n, edges: e } = get();
        set({ edges: recomputeEdgeHandles(n, e) });
      },

      setSuggestions: (suggestions) => {
        set({ suggestions });
      },

      setIsSuggestionsLoading: (loading) => {
        set({ isSuggestionsLoading: loading });
      },

      acceptSuggestion: (id) => {
        const { suggestions } = get();
        const suggestion = suggestions.find((s) => s.id === id);

        if (!suggestion) return;

        if (suggestion.type === 'connection' && suggestion.sourceNodeId && suggestion.targetNodeId) {
          get().addEdge(
            suggestion.sourceNodeId,
            suggestion.targetNodeId,
            suggestion.suggestedRelationship ?? null
          );
        } else if (suggestion.type === 'cluster' && suggestion.targetNodeId) {
          const clusterMatch = suggestion.description.match(/cluster (\d)/i);
          if (clusterMatch) {
            const cluster = parseInt(clusterMatch[1]) as 1 | 2 | 3 | 4 | 5;
            get().updateNodeData(suggestion.targetNodeId, { cluster });
          }
        }

        get().dismissSuggestion(id);
      },

      dismissSuggestion: (id) => {
        set((state) => ({
          suggestions: state.suggestions.filter((s) => s.id !== id),
        }));
      },

      setClusterName: (cluster, name) => {
        set((state) => ({
          clusterNames: { ...state.clusterNames, [cluster]: name },
        }));
      },

      setScaffold: (scaffold) => {
        set({ scaffold });
      },

      repairOrphans: () => {
        const { nodes, edges } = get();

        // Ensure root node exists
        let rootNode = nodes.find((n) => n.id === 'root');
        const updatedNodes = [...nodes];
        const updatedEdges = [...edges];

        if (!rootNode) {
          const avgX = nodes.length > 0
            ? nodes.reduce((sum, n) => sum + n.position.x, 0) / nodes.length
            : 400;
          const avgY = nodes.length > 0
            ? nodes.reduce((sum, n) => sum + n.position.y, 0) / nodes.length
            : 200;
          rootNode = {
            id: 'root',
            type: 'mindMapNode',
            position: { x: avgX, y: avgY },
            data: { title: 'Main Ideas', body: '', cluster: 1 as const },
          };
          updatedNodes.unshift(rootNode);
        }

        // Find all nodes connected to root (directly or indirectly)
        const connectedToRoot = new Set<string>(['root']);
        let changed = true;
        while (changed) {
          changed = false;
          for (const edge of updatedEdges) {
            if (connectedToRoot.has(edge.source) && !connectedToRoot.has(edge.target)) {
              connectedToRoot.add(edge.target);
              changed = true;
            }
            if (connectedToRoot.has(edge.target) && !connectedToRoot.has(edge.source)) {
              connectedToRoot.add(edge.source);
              changed = true;
            }
          }
        }

        // Connect orphans to root
        let repaired = false;
        for (const node of updatedNodes) {
          if (node.id !== 'root' && !connectedToRoot.has(node.id)) {
            const handles = pickHandles(rootNode.position, node.position);
            updatedEdges.push({
              id: `edge-root-${node.id}`,
              source: 'root',
              target: node.id,
              data: { relationship: null },
              ...handles,
            });
            repaired = true;
          }
        }

        // If root has no title, derive one
        if (!rootNode.data.title) {
          const childTitles = updatedNodes
            .filter((n) => n.id !== 'root' && n.data.title)
            .map((n) => n.data.title);
          rootNode.data = {
            ...rootNode.data,
            title: childTitles.length > 0
              ? childTitles.sort((a, b) => a.length - b.length)[0]
              : 'Main Ideas',
          };
          repaired = true;
        }

        // Center root among children
        const children = updatedNodes.filter((n) => n.id !== 'root');
        if (children.length > 0) {
          const centerX = children.reduce((sum, n) => sum + n.position.x, 0) / children.length;
          const centerY = children.reduce((sum, n) => sum + n.position.y, 0) / children.length;
          const root = updatedNodes.find((n) => n.id === 'root')!;
          root.position = { x: centerX, y: centerY };
          repaired = true;
        }

        if (repaired) {
          set({
            nodes: updatedNodes,
            edges: recomputeEdgeHandles(updatedNodes, updatedEdges),
          });
        }
      },

      setActiveDocument: (docId: string) => {
        const state = get();
        const oldDocId = state._activeDocumentId;

        // No-op if already active
        if (oldDocId === docId) return;

        // Save current working copy for old document
        const nextMaps = { ...state.maps };
        const nextTransient = { ...state._transientMap };

        if (oldDocId) {
          nextMaps[oldDocId] = {
            nodes: state.nodes,
            edges: state.edges,
            scaffold: state.scaffold,
            clusterNames: state.clusterNames,
          };
          nextTransient[oldDocId] = {
            suggestions: state.suggestions,
            isSuggestionsLoading: state.isSuggestionsLoading,
            _past: state._past,
            _future: state._future,
          };
        }

        // Load data for new document (or fresh defaults)
        const docData = nextMaps[docId] ?? emptyDocumentData();
        const transientData = nextTransient[docId] ?? emptyTransientData();

        set({
          _activeDocumentId: docId,
          maps: nextMaps,
          _transientMap: nextTransient,
          nodes: docData.nodes,
          edges: docData.edges,
          scaffold: docData.scaffold,
          clusterNames: docData.clusterNames,
          suggestions: transientData.suggestions,
          isSuggestionsLoading: transientData.isSuggestionsLoading,
          _past: transientData._past,
          _future: transientData._future,
        });
      },

      deleteDocumentMap: (docId: string) => {
        set((state) => {
          const nextMaps = { ...state.maps };
          const nextTransient = { ...state._transientMap };
          delete nextMaps[docId];
          delete nextTransient[docId];
          return { maps: nextMaps, _transientMap: nextTransient };
        });
      },

      resetMindMap: () => {
        const state = get();
        const activeId = state._activeDocumentId;

        // Clear persisted data for active document
        const nextMaps = { ...state.maps };
        const nextTransient = { ...state._transientMap };
        if (activeId) {
          delete nextMaps[activeId];
          delete nextTransient[activeId];
        }

        set({
          nodes: [defaultNode],
          edges: [],
          suggestions: [],
          scaffold: null,
          clusterNames: { ...DEFAULT_CLUSTER_NAMES },
          _past: [],
          _future: [],
          maps: nextMaps,
          _transientMap: nextTransient,
        });
      },
    }),
    {
      name: 'dyslex-mindmap',
      storage: createUserScopedStorage(),
      skipHydration: true,
      version: 4,
      partialize: (state) => {
        // Flush working copy into maps before serializing
        const maps = { ...state.maps };
        if (state._activeDocumentId) {
          maps[state._activeDocumentId] = {
            nodes: state.nodes,
            edges: state.edges,
            scaffold: state.scaffold,
            clusterNames: state.clusterNames,
          };
        }
        return {
          maps,
          _activeDocumentId: state._activeDocumentId,
        };
      },
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        // Load working copy from maps for the active document
        const activeId = state._activeDocumentId;
        if (activeId && state.maps[activeId]) {
          const docData = state.maps[activeId];
          state.nodes = docData.nodes;
          state.edges = docData.edges;
          state.scaffold = docData.scaffold;
          state.clusterNames = docData.clusterNames;
        }
      },
      migrate: (persisted: any, version: number) => {
        if (version === 0) {
          // Backfill edge data for edges saved before relationship support
          const state = persisted as any;
          if (state.edges) {
            state.edges = state.edges.map((edge: any) => ({
              ...edge,
              data: edge.data ?? { relationship: null },
            }));
          }
        }
        if (version < 2) {
          // Backfill cluster names
          const state = persisted as any;
          if (!state.clusterNames) {
            state.clusterNames = { ...DEFAULT_CLUSTER_NAMES };
          }
        }
        if (version < 3) {
          // Ensure root node exists and all nodes connect to it
          const state = persisted as any;
          const nodes: any[] = state.nodes || [];
          const edges: any[] = state.edges || [];

          // Ensure root node exists
          let rootNode = nodes.find((n: any) => n.id === 'root');
          if (!rootNode) {
            // Compute center of all existing nodes for root placement
            const avgX = nodes.length > 0
              ? nodes.reduce((sum: number, n: any) => sum + (n.position?.x || 0), 0) / nodes.length
              : 400;
            const avgY = nodes.length > 0
              ? nodes.reduce((sum: number, n: any) => sum + (n.position?.y || 0), 0) / nodes.length
              : 200;
            rootNode = {
              id: 'root',
              type: 'mindMapNode',
              position: { x: avgX, y: avgY },
              data: { title: '', body: '', cluster: 1 },
            };
            nodes.unshift(rootNode);
          }

          // Find orphaned nodes (no edge connecting them to root, directly or indirectly)
          const connectedToRoot = new Set<string>(['root']);
          let changed = true;
          while (changed) {
            changed = false;
            for (const edge of edges) {
              if (connectedToRoot.has(edge.source) && !connectedToRoot.has(edge.target)) {
                connectedToRoot.add(edge.target);
                changed = true;
              }
              if (connectedToRoot.has(edge.target) && !connectedToRoot.has(edge.source)) {
                connectedToRoot.add(edge.source);
                changed = true;
              }
            }
          }

          // Connect orphaned nodes to root
          for (const node of nodes) {
            if (node.id !== 'root' && !connectedToRoot.has(node.id)) {
              edges.push({
                id: `edge-root-${node.id}`,
                source: 'root',
                target: node.id,
                data: { relationship: null },
              });
            }
          }

          // If root has no title, derive one from child nodes
          if (!rootNode.data.title) {
            const childTitles = nodes
              .filter((n: any) => n.id !== 'root' && n.data?.title)
              .map((n: any) => n.data.title);
            if (childTitles.length > 0) {
              rootNode.data.title = childTitles.sort((a: string, b: string) => a.length - b.length)[0];
            } else {
              rootNode.data.title = 'Main Ideas';
            }
          }

          // Center root among its children
          const children = nodes.filter((n: any) => n.id !== 'root');
          if (children.length > 0) {
            rootNode.position = {
              x: children.reduce((sum: number, n: any) => sum + (n.position?.x || 0), 0) / children.length,
              y: children.reduce((sum: number, n: any) => sum + (n.position?.y || 0), 0) / children.length,
            };
          }

          state.nodes = nodes;
          state.edges = edges;
        }
        if (version < 4) {
          // Migrate from v3 (top-level nodes/edges) to v4 (per-document maps)
          const state = persisted as any;
          const DEFAULT_DOC_ID = '00000000-0000-4000-8000-000000000001';

          const docData: DocumentMindMapData = {
            nodes: state.nodes || [{ ...defaultNode, data: { ...defaultNode.data } }],
            edges: state.edges || [],
            scaffold: state.scaffold || null,
            clusterNames: state.clusterNames || { ...DEFAULT_CLUSTER_NAMES },
          };

          state.maps = { [DEFAULT_DOC_ID]: docData };
          state._activeDocumentId = DEFAULT_DOC_ID;

          // Clean up old top-level fields (they'll be populated from maps on rehydrate)
          delete state.nodes;
          delete state.edges;
          delete state.scaffold;
          delete state.clusterNames;
        }
        return persisted;
      },
    }
  )
);

registerScopedStore(() => useMindMapStore.persist.rehydrate());

// --- Subscribe to document store changes ---
// Lazy import to avoid circular dependency: documentStore imports are deferred
// until the subscription fires (after both stores are initialized).
let _documentStoreSubscribed = false;
let _lastDocIds: Set<string> | null = null;

function ensureDocumentSubscription() {
  if (_documentStoreSubscribed) return;
  _documentStoreSubscribed = true;

  // Dynamically import to avoid circular dependency at module init
  import('./documentStore').then(({ useDocumentStore }) => {
    // Set initial active document
    const docState = useDocumentStore.getState();
    if (docState.activeDocumentId) {
      useMindMapStore.getState().setActiveDocument(docState.activeDocumentId);
    }
    _lastDocIds = new Set(docState.documents.map((d) => d.id));

    useDocumentStore.subscribe((state, prevState) => {
      // Handle active document change
      if (state.activeDocumentId && state.activeDocumentId !== prevState.activeDocumentId) {
        useMindMapStore.getState().setActiveDocument(state.activeDocumentId);
      }

      // Handle document deletions
      const currentIds = new Set(state.documents.map((d) => d.id));
      if (_lastDocIds) {
        for (const id of _lastDocIds) {
          if (!currentIds.has(id)) {
            useMindMapStore.getState().deleteDocumentMap(id);
          }
        }
      }
      _lastDocIds = currentIds;
    });
  });
}

// Kick off subscription after module loads
// Using setTimeout(0) ensures both stores are fully initialized
setTimeout(ensureDocumentSubscription, 0);
