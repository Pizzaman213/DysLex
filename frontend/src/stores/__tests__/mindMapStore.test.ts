import { describe, it, expect, beforeEach } from 'vitest';
import { useMindMapStore } from '../mindMapStore';

const defaultRootNode = {
  id: 'root',
  type: 'mindMapNode',
  position: { x: 400, y: 200 },
  data: { title: '', body: '', cluster: 1 },
};

describe('mindMapStore', () => {
  beforeEach(() => {
    useMindMapStore.getState().resetMindMap();
  });

  // ---------- Default state ----------

  it('has correct default state', () => {
    const state = useMindMapStore.getState();
    expect(state.nodes).toHaveLength(1);
    expect(state.nodes[0]).toMatchObject(defaultRootNode);
    expect(state.edges).toEqual([]);
    expect(state.suggestions).toEqual([]);
    expect(state.isSuggestionsLoading).toBe(false);
    expect(state.scaffold).toBeNull();
    expect(state.clusterNames).toEqual({
      1: 'Cluster 1',
      2: 'Cluster 2',
      3: 'Cluster 3',
      4: 'Cluster 4',
      5: 'Cluster 5',
    });
    expect(state._past).toEqual([]);
    expect(state._future).toEqual([]);
  });

  // ---------- Node CRUD ----------

  describe('Node CRUD', () => {
    it('addNode creates a new node and edge from parent', () => {
      useMindMapStore.getState().addNode('root', { x: 600, y: 300 }, { title: 'Child' });

      const state = useMindMapStore.getState();
      expect(state.nodes).toHaveLength(2);

      const child = state.nodes.find((n) => n.id !== 'root');
      expect(child).toBeDefined();
      expect(child!.data.title).toBe('Child');

      expect(state.edges).toHaveLength(1);
      expect(state.edges[0].source).toBe('root');
      expect(state.edges[0].target).toBe(child!.id);
    });

    it('addNode without parent creates orphan node', () => {
      useMindMapStore.getState().addNode(null, { x: 100, y: 100 }, { title: 'Orphan' });

      const state = useMindMapStore.getState();
      expect(state.nodes).toHaveLength(2);
      expect(state.edges).toHaveLength(0);
    });

    it('updateNodeData updates data for a specific node', () => {
      useMindMapStore.getState().updateNodeData('root', { title: 'Updated Title' });

      const root = useMindMapStore.getState().nodes[0];
      expect(root.data.title).toBe('Updated Title');
      expect(root.data.body).toBe('');
    });

    it('updateNodePosition updates position', () => {
      useMindMapStore.getState().updateNodePosition('root', { x: 100, y: 100 });

      const root = useMindMapStore.getState().nodes[0];
      expect(root.position).toEqual({ x: 100, y: 100 });
    });

    it('deleteNode removes node and connected edges', () => {
      useMindMapStore.getState().addNode('root', { x: 600, y: 300 }, { title: 'Child' });
      const childId = useMindMapStore.getState().nodes.find((n) => n.id !== 'root')!.id;

      useMindMapStore.getState().deleteNode(childId);

      const state = useMindMapStore.getState();
      expect(state.nodes).toHaveLength(1);
      expect(state.nodes[0].id).toBe('root');
      expect(state.edges).toHaveLength(0);
    });

    it('deleteNode does not delete root node', () => {
      useMindMapStore.getState().deleteNode('root');

      expect(useMindMapStore.getState().nodes).toHaveLength(1);
      expect(useMindMapStore.getState().nodes[0].id).toBe('root');
    });

    it('quickAddNode adds node connected to root with formatted title', () => {
      useMindMapStore.getState().quickAddNode('hello world', { x: 500, y: 400 });

      const state = useMindMapStore.getState();
      expect(state.nodes).toHaveLength(2);

      const child = state.nodes.find((n) => n.id !== 'root');
      expect(child).toBeDefined();
      expect(child!.data.title).toBe('Hello world');

      expect(state.edges).toHaveLength(1);
      expect(state.edges[0].source).toBe('root');
    });

    it('quickAddNode truncates long titles', () => {
      const longText = 'a'.repeat(80);
      useMindMapStore.getState().quickAddNode(longText, { x: 500, y: 400 });

      const child = useMindMapStore.getState().nodes.find((n) => n.id !== 'root');
      expect(child!.data.title.length).toBeLessThanOrEqual(60);
      expect(child!.data.title.endsWith('...')).toBe(true);
      // Long text goes in body as-is (no capitalization)
      expect(child!.data.body).toBe(longText);
    });
  });

  // ---------- Edge CRUD ----------

  describe('Edge CRUD', () => {
    it('addEdge creates a new edge between nodes', () => {
      useMindMapStore.getState().addNode(null, { x: 600, y: 300 }, { title: 'Node B' });
      const nodeB = useMindMapStore.getState().nodes.find((n) => n.id !== 'root')!;

      useMindMapStore.getState().addEdge('root', nodeB.id, 'supports');

      const edges = useMindMapStore.getState().edges;
      expect(edges).toHaveLength(1);
      expect(edges[0].source).toBe('root');
      expect(edges[0].target).toBe(nodeB.id);
      expect(edges[0].data?.relationship).toBe('supports');
    });

    it('addEdge does not create duplicate edges', () => {
      useMindMapStore.getState().addNode(null, { x: 600, y: 300 });
      const nodeB = useMindMapStore.getState().nodes.find((n) => n.id !== 'root')!;

      useMindMapStore.getState().addEdge('root', nodeB.id);
      useMindMapStore.getState().addEdge('root', nodeB.id);

      expect(useMindMapStore.getState().edges).toHaveLength(1);
    });

    it('updateEdgeData updates edge data', () => {
      useMindMapStore.getState().addNode(null, { x: 600, y: 300 });
      const nodeB = useMindMapStore.getState().nodes.find((n) => n.id !== 'root')!;
      useMindMapStore.getState().addEdge('root', nodeB.id, 'supports');

      const edgeId = useMindMapStore.getState().edges[0].id;
      useMindMapStore.getState().updateEdgeData(edgeId, { relationship: 'contradicts' });

      expect(useMindMapStore.getState().edges[0].data?.relationship).toBe('contradicts');
    });

    it('deleteEdge removes edge by id', () => {
      useMindMapStore.getState().addNode(null, { x: 600, y: 300 });
      const nodeB = useMindMapStore.getState().nodes.find((n) => n.id !== 'root')!;
      useMindMapStore.getState().addEdge('root', nodeB.id);

      const edgeId = useMindMapStore.getState().edges[0].id;
      useMindMapStore.getState().deleteEdge(edgeId);

      expect(useMindMapStore.getState().edges).toHaveLength(0);
    });
  });

  // ---------- Undo / Redo ----------

  describe('Undo / Redo', () => {
    it('canUndo returns false initially', () => {
      expect(useMindMapStore.getState().canUndo()).toBe(false);
    });

    it('canRedo returns false initially', () => {
      expect(useMindMapStore.getState().canRedo()).toBe(false);
    });

    it('undo restores previous state after addNode', () => {
      useMindMapStore.getState().addNode('root', { x: 600, y: 300 }, { title: 'Child' });
      expect(useMindMapStore.getState().nodes).toHaveLength(2);
      expect(useMindMapStore.getState().canUndo()).toBe(true);

      useMindMapStore.getState().undo();
      expect(useMindMapStore.getState().nodes).toHaveLength(1);
      expect(useMindMapStore.getState().nodes[0].id).toBe('root');
    });

    it('redo restores state after undo', () => {
      useMindMapStore.getState().addNode('root', { x: 600, y: 300 }, { title: 'Child' });
      useMindMapStore.getState().undo();
      expect(useMindMapStore.getState().canRedo()).toBe(true);

      useMindMapStore.getState().redo();
      expect(useMindMapStore.getState().nodes).toHaveLength(2);
    });

    it('new action clears redo stack', () => {
      useMindMapStore.getState().addNode('root', { x: 600, y: 300 }, { title: 'A' });
      useMindMapStore.getState().undo();
      expect(useMindMapStore.getState().canRedo()).toBe(true);

      useMindMapStore.getState().addNode('root', { x: 700, y: 400 }, { title: 'B' });
      expect(useMindMapStore.getState().canRedo()).toBe(false);
    });

    it('undo does nothing when no history', () => {
      const nodesBefore = useMindMapStore.getState().nodes;
      useMindMapStore.getState().undo();
      expect(useMindMapStore.getState().nodes).toEqual(nodesBefore);
    });

    it('redo does nothing when no future', () => {
      const nodesBefore = useMindMapStore.getState().nodes;
      useMindMapStore.getState().redo();
      expect(useMindMapStore.getState().nodes).toEqual(nodesBefore);
    });

    it('updateNodePosition does not push history', () => {
      useMindMapStore.getState().updateNodePosition('root', { x: 100, y: 100 });
      expect(useMindMapStore.getState().canUndo()).toBe(false);
    });

    it('history is capped at 50 entries', () => {
      for (let i = 0; i < 60; i++) {
        useMindMapStore.getState().updateNodeData('root', { title: `Title ${i}` });
      }
      expect(useMindMapStore.getState()._past.length).toBeLessThanOrEqual(50);
    });
  });

  // ---------- Suggestions ----------

  describe('Suggestions', () => {
    it('setSuggestions sets suggestions array', () => {
      const suggestions = [
        {
          id: 's1', type: 'connection' as const,
          sourceNodeId: 'root', targetNodeId: 'n1',
          description: 'Connect these', suggestedRelationship: 'supports' as const,
        },
      ];
      useMindMapStore.getState().setSuggestions(suggestions);
      expect(useMindMapStore.getState().suggestions).toEqual(suggestions);
    });

    it('dismissSuggestion removes suggestion by id', () => {
      useMindMapStore.getState().setSuggestions([
        { id: 's1', type: 'gap', description: 'A' },
        { id: 's2', type: 'gap', description: 'B' },
      ]);
      useMindMapStore.getState().dismissSuggestion('s1');

      const remaining = useMindMapStore.getState().suggestions;
      expect(remaining).toHaveLength(1);
      expect(remaining[0].id).toBe('s2');
    });

    it('acceptSuggestion for connection creates edge and removes suggestion', () => {
      useMindMapStore.getState().addNode(null, { x: 600, y: 300 }, { title: 'Target' });
      const targetId = useMindMapStore.getState().nodes.find((n) => n.id !== 'root')!.id;

      useMindMapStore.getState().setSuggestions([
        {
          id: 's1', type: 'connection',
          sourceNodeId: 'root', targetNodeId: targetId,
          description: 'Connect', suggestedRelationship: 'leads_to',
        },
      ]);

      useMindMapStore.getState().acceptSuggestion('s1');

      expect(useMindMapStore.getState().suggestions).toHaveLength(0);
      const edges = useMindMapStore.getState().edges;
      expect(edges.some((e) => e.source === 'root' && e.target === targetId)).toBe(true);
    });

    it('setIsSuggestionsLoading updates loading flag', () => {
      useMindMapStore.getState().setIsSuggestionsLoading(true);
      expect(useMindMapStore.getState().isSuggestionsLoading).toBe(true);
      useMindMapStore.getState().setIsSuggestionsLoading(false);
      expect(useMindMapStore.getState().isSuggestionsLoading).toBe(false);
    });
  });

  // ---------- Cluster Names ----------

  describe('Cluster Names', () => {
    it('setClusterName updates specific cluster name', () => {
      useMindMapStore.getState().setClusterName(1, 'Introduction');
      useMindMapStore.getState().setClusterName(3, 'Evidence');

      const names = useMindMapStore.getState().clusterNames;
      expect(names[1]).toBe('Introduction');
      expect(names[2]).toBe('Cluster 2'); // unchanged
      expect(names[3]).toBe('Evidence');
    });
  });

  // ---------- Scaffold ----------

  describe('Scaffold', () => {
    it('setScaffold sets scaffold', () => {
      const scaffold = {
        title: 'Essay Structure',
        sections: [
          { heading: 'Intro', hint: 'Start here', nodeIds: ['root'] },
        ],
      };
      useMindMapStore.getState().setScaffold(scaffold);
      expect(useMindMapStore.getState().scaffold).toEqual(scaffold);
    });

    it('setScaffold(null) clears scaffold', () => {
      useMindMapStore.getState().setScaffold({
        title: 'Test', sections: [],
      });
      useMindMapStore.getState().setScaffold(null);
      expect(useMindMapStore.getState().scaffold).toBeNull();
    });
  });

  // ---------- Batch Update ----------

  describe('batchUpdate', () => {
    it('groups multiple operations into single history entry', () => {
      useMindMapStore.getState().batchUpdate(() => {
        useMindMapStore.getState().updateNodeData('root', { title: 'Step 1' });
        useMindMapStore.getState().updateNodeData('root', { title: 'Step 2' });
      });

      // Only one history entry for the batch
      expect(useMindMapStore.getState()._past).toHaveLength(1);
      expect(useMindMapStore.getState().nodes[0].data.title).toBe('Step 2');
    });
  });

  // ---------- Reset ----------

  describe('resetMindMap', () => {
    it('clears all state back to defaults', () => {
      useMindMapStore.getState().addNode('root', { x: 600, y: 300 }, { title: 'Child' });
      useMindMapStore.getState().setSuggestions([{ id: 's1', type: 'gap', description: 'A' }]);
      useMindMapStore.getState().setScaffold({ title: 'Test', sections: [] });
      useMindMapStore.getState().setClusterName(1, 'Custom');

      useMindMapStore.getState().resetMindMap();

      const state = useMindMapStore.getState();
      expect(state.nodes).toHaveLength(1);
      expect(state.nodes[0].id).toBe('root');
      expect(state.edges).toEqual([]);
      expect(state.suggestions).toEqual([]);
      expect(state.scaffold).toBeNull();
      expect(state.clusterNames[1]).toBe('Cluster 1');
      expect(state._past).toEqual([]);
      expect(state._future).toEqual([]);
    });
  });
});
