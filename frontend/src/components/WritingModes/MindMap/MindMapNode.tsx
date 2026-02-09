import { memo, useState, useCallback, useRef, useEffect } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { useMindMapStore } from '../../../stores/mindMapStore';
import { MindMapNodeData } from './types';

export const MindMapNode = memo(({ id, data }: NodeProps) => {
  const nodeData = data as MindMapNodeData;
  const [isEditing, setIsEditing] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [editTitle, setEditTitle] = useState(nodeData.title);
  const [editBody, setEditBody] = useState(nodeData.body);
  const [editCluster, setEditCluster] = useState(nodeData.cluster);
  const titleInputRef = useRef<HTMLInputElement>(null);
  const updateNodeData = useMindMapStore((state) => state.updateNodeData);
  const addNode = useMindMapStore((state) => state.addNode);
  const deleteNode = useMindMapStore((state) => state.deleteNode);
  const edges = useMindMapStore((state) => state.edges);
  const clusterNames = useMindMapStore((state) => state.clusterNames);

  const isRoot = id === 'root';

  // Determine if this is a sub-node (child of a non-root node)
  const isSub = !isRoot && !edges.some((e) => e.target === id && e.source === 'root');

  useEffect(() => {
    if (isEditing && titleInputRef.current) {
      titleInputRef.current.focus();
      titleInputRef.current.select();
    }
  }, [isEditing]);

  const handleDoubleClick = useCallback(() => {
    setIsEditing(true);
  }, []);

  const handleSave = useCallback(() => {
    updateNodeData(id, {
      title: editTitle.trim() || 'Untitled',
      body: editBody,
      cluster: editCluster,
    });
    setIsEditing(false);
  }, [id, editTitle, editBody, editCluster, updateNodeData]);

  const handleCancel = useCallback(() => {
    setEditTitle(nodeData.title);
    setEditBody(nodeData.body);
    setEditCluster(nodeData.cluster);
    setIsEditing(false);
  }, [nodeData]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation();
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSave();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
    },
    [handleSave, handleCancel]
  );

  const handleAddChild = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      const nodes = useMindMapStore.getState().nodes;
      const currentNode = nodes.find((n) => n.id === id);
      if (currentNode) {
        addNode(id, {
          x: currentNode.position.x + 200,
          y: currentNode.position.y + Math.random() * 100 - 50,
        });
      }
    },
    [id, addNode]
  );

  const handleDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (isRoot) return;
      setShowDelete(true);
    },
    [isRoot]
  );

  const confirmDelete = useCallback(() => {
    deleteNode(id);
    setShowDelete(false);
  }, [id, deleteNode]);

  const cancelDelete = useCallback(() => {
    setShowDelete(false);
  }, []);

  const nodeClasses = [
    'mindmap-node',
    isRoot ? 'central' : '',
    !isRoot ? `n${nodeData.cluster}` : '',
    isSub ? 'sub' : '',
    isEditing ? 'editing' : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={nodeClasses}
      onDoubleClick={handleDoubleClick}
    >
      {/* Handles on all four sides so edges connect from the closest side */}
      <Handle type="target" position={Position.Left} id="target-left" className="mindmap-handle" />
      <Handle type="target" position={Position.Right} id="target-right" className="mindmap-handle" />
      <Handle type="target" position={Position.Top} id="target-top" className="mindmap-handle" />
      <Handle type="target" position={Position.Bottom} id="target-bottom" className="mindmap-handle" />
      <Handle type="source" position={Position.Left} id="source-left" className="mindmap-handle" />
      <Handle type="source" position={Position.Right} id="source-right" className="mindmap-handle" />
      <Handle type="source" position={Position.Top} id="source-top" className="mindmap-handle" />
      <Handle type="source" position={Position.Bottom} id="source-bottom" className="mindmap-handle" />

      {isEditing ? (
        <div className="mindmap-node-edit" onClick={(e) => e.stopPropagation()}>
          <input
            ref={titleInputRef}
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            className="mindmap-node-title-input"
            placeholder="Title"
            aria-label="Edit node title"
          />
          <textarea
            value={editBody}
            onChange={(e) => setEditBody(e.target.value)}
            onKeyDown={handleKeyDown}
            className="mindmap-node-body-input"
            placeholder="Details (optional)"
            aria-label="Edit node details"
            rows={2}
          />
          <div className="mindmap-node-cluster-picker">
            <span className="cluster-label">Group:</span>
            {([1, 2, 3, 4, 5] as const).map((cluster) => (
              <button
                key={cluster}
                type="button"
                onClick={() => setEditCluster(cluster)}
                className={`cluster-dot ${editCluster === cluster ? 'active' : ''}`}
                style={{ backgroundColor: `var(--color-cluster-${cluster})` }}
                aria-label={clusterNames[cluster]}
                aria-pressed={editCluster === cluster}
                title={clusterNames[cluster]}
              />
            ))}
          </div>
          <div className="mindmap-node-actions">
            <button
              type="button"
              onClick={handleSave}
              className="btn-save"
              aria-label="Save changes"
            >
              Save
            </button>
            <button
              type="button"
              onClick={handleCancel}
              className="btn-cancel"
              aria-label="Cancel editing"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mindmap-node-content">
          <div className="mindmap-node-title">{nodeData.title}</div>
          {nodeData.body && <div className="mindmap-node-body">{nodeData.body}</div>}
          <div className="mindmap-node-hover-actions">
            <button
              type="button"
              onClick={handleAddChild}
              className="btn-add"
              aria-label="Add child node"
              title="Add child"
            >
              +
            </button>
            {!isRoot && (
              <button
                type="button"
                onClick={handleDelete}
                className="btn-delete"
                aria-label="Delete node"
                title="Delete"
              >
                ×
              </button>
            )}
          </div>
        </div>
      )}

      {showDelete && (
        <div
          className="mindmap-delete-confirmation"
          role="alertdialog"
          aria-labelledby="delete-title"
          aria-describedby="delete-desc"
          onClick={(e) => e.stopPropagation()}
        >
          <div id="delete-title" className="delete-title">
            Remove "{nodeData.title}"?
          </div>
          <div id="delete-desc" className="delete-desc">
            This will remove the node and its connections.
          </div>
          <div className="delete-actions">
            <button
              type="button"
              onClick={confirmDelete}
              className="btn-confirm-delete"
              aria-label="Confirm deletion"
            >
              Delete
            </button>
            <button
              type="button"
              onClick={cancelDelete}
              className="btn-cancel-delete"
              aria-label="Cancel deletion"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
});

MindMapNode.displayName = 'MindMapNode';
