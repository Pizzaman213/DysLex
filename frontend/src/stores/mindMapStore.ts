import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  MindMapFlowNode,
  MindMapFlowEdge,
  MindMapNodeData,
  AISuggestion,
  Scaffold,
} from '../components/WritingModes/MindMap/types';

interface MindMapState {
  nodes: MindMapFlowNode[];
  edges: MindMapFlowEdge[];
  suggestions: AISuggestion[];
  isSuggestionsLoading: boolean;
  scaffold: Scaffold | null;

  // Node CRUD
  addNode: (
    parentId: string | null,
    position: { x: number; y: number },
    data?: Partial<MindMapNodeData>
  ) => void;
  updateNodeData: (id: string, partial: Partial<MindMapNodeData>) => void;
  updateNodePosition: (id: string, position: { x: number; y: number }) => void;
  deleteNode: (id: string) => void;

  // Edge CRUD
  addEdge: (source: string, target: string) => void;
  deleteEdge: (id: string) => void;

  // Suggestions
  setSuggestions: (suggestions: AISuggestion[]) => void;
  setIsSuggestionsLoading: (loading: boolean) => void;
  acceptSuggestion: (id: string) => void;
  dismissSuggestion: (id: string) => void;

  // Scaffold
  setScaffold: (scaffold: Scaffold | null) => void;

  // Reset
  resetMindMap: () => void;
}

const defaultNode: MindMapFlowNode = {
  id: 'root',
  type: 'mindMapNode',
  position: { x: 400, y: 200 },
  data: { title: 'Main Idea', body: '', cluster: 1 },
};

export const useMindMapStore = create<MindMapState>()(
  persist(
    (set, get) => ({
      nodes: [defaultNode],
      edges: [],
      suggestions: [],
      isSuggestionsLoading: false,
      scaffold: null,

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

        set((state) => ({
          nodes: [...state.nodes, newNode],
          edges: parentId
            ? [
                ...state.edges,
                {
                  id: `edge-${parentId}-${newNode.id}`,
                  source: parentId,
                  target: newNode.id,
                },
              ]
            : state.edges,
        }));
      },

      updateNodeData: (id, partial) => {
        set((state) => ({
          nodes: state.nodes.map((node) =>
            node.id === id
              ? { ...node, data: { ...node.data, ...partial } }
              : node
          ),
        }));
      },

      updateNodePosition: (id, position) => {
        set((state) => ({
          nodes: state.nodes.map((node) =>
            node.id === id ? { ...node, position } : node
          ),
        }));
      },

      deleteNode: (id) => {
        if (id === 'root') return; // Cannot delete root node

        set((state) => ({
          nodes: state.nodes.filter((node) => node.id !== id),
          edges: state.edges.filter(
            (edge) => edge.source !== id && edge.target !== id
          ),
        }));
      },

      addEdge: (source, target) => {
        const { edges } = get();
        const edgeExists = edges.some(
          (edge) => edge.source === source && edge.target === target
        );

        if (!edgeExists) {
          const newEdge: MindMapFlowEdge = {
            id: `edge-${source}-${target}`,
            source,
            target,
          };
          set((state) => ({ edges: [...state.edges, newEdge] }));
        }
      },

      deleteEdge: (id) => {
        set((state) => ({
          edges: state.edges.filter((edge) => edge.id !== id),
        }));
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
          get().addEdge(suggestion.sourceNodeId, suggestion.targetNodeId);
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

      setScaffold: (scaffold) => {
        set({ scaffold });
      },

      resetMindMap: () => {
        set({
          nodes: [defaultNode],
          edges: [],
          suggestions: [],
          scaffold: null,
        });
      },
    }),
    {
      name: 'dyslex-mindmap',
      partialize: (state) => ({
        nodes: state.nodes,
        edges: state.edges,
        scaffold: state.scaffold,
      }),
    }
  )
);
