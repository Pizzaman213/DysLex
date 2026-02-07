import { useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  pointerWithin,
  closestCenter,
  CollisionDetection,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useDocumentStore } from '@/stores/documentStore';
import { SortableDocItem } from './SortableDocItem';
import { FolderItem } from './FolderItem';

const collisionDetection: CollisionDetection = (args) => {
  // First check for pointer-within collisions (folder drop targets)
  const pointerCollisions = pointerWithin(args);
  const folderDropTarget = pointerCollisions.find((c) =>
    String(c.id).startsWith('droppable-')
  );
  if (folderDropTarget) {
    return [folderDropTarget];
  }

  // Fall back to closest center for reordering
  return closestCenter(args);
};

export function DocumentList() {
  const documents = useDocumentStore((s) => s.documents);
  const folders = useDocumentStore((s) => s.folders);
  const rootOrder = useDocumentStore((s) => s.rootOrder);
  const folderOrders = useDocumentStore((s) => s.folderOrders);
  const createDocument = useDocumentStore((s) => s.createDocument);
  const createFolder = useDocumentStore((s) => s.createFolder);
  const moveDocumentToFolder = useDocumentStore((s) => s.moveDocumentToFolder);
  const reorderRoot = useDocumentStore((s) => s.reorderRoot);
  const reorderInFolder = useDocumentStore((s) => s.reorderInFolder);

  const [activeId, setActiveId] = useState<string | null>(null);
  const [dragOverFolderId, setDragOverFolderId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor)
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const handleDragOver = (event: DragEndEvent) => {
    const { over } = event;
    if (over && String(over.id).startsWith('droppable-')) {
      const folderId = String(over.id).replace('droppable-', '');
      setDragOverFolderId(folderId);
    } else {
      setDragOverFolderId(null);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    setDragOverFolderId(null);

    if (!over) return;

    const activeIdStr = String(active.id);
    const overIdStr = String(over.id);
    const activeData = active.data.current as { type: string; folderId?: string | null } | undefined;

    // Only handle document drags (not folder-on-folder)
    if (activeData?.type !== 'document') {
      // Folder reorder in root
      if (activeData?.type === 'folder' && activeIdStr !== overIdStr) {
        // If dropped on another root-level item, reorder
        if (rootOrder.includes(overIdStr)) {
          reorderRoot(activeIdStr, overIdStr);
        }
      }
      return;
    }

    const docFolderId = activeData.folderId ?? null;

    // Case 1: Document dropped on a folder droppable
    if (overIdStr.startsWith('droppable-')) {
      const targetFolderId = overIdStr.replace('droppable-', '');
      if (docFolderId !== targetFolderId) {
        moveDocumentToFolder(activeIdStr, targetFolderId);
      }
      return;
    }

    // Case 2: Document dropped on a folder sortable item
    const overData = over.data.current as { type: string; folderId?: string | null } | undefined;
    if (overData?.type === 'folder') {
      moveDocumentToFolder(activeIdStr, overIdStr);
      return;
    }

    // Case 3: Reorder within the same context
    if (activeIdStr === overIdStr) return;

    const overFolderId = overData?.folderId ?? null;

    if (docFolderId && docFolderId === overFolderId) {
      // Reorder within same folder
      reorderInFolder(docFolderId, activeIdStr, overIdStr);
    } else if (!docFolderId && !overFolderId) {
      // Reorder within root
      reorderRoot(activeIdStr, overIdStr);
    } else {
      // Cross-context: move doc to the target's context
      const targetFolder = overFolderId ?? null;
      moveDocumentToFolder(activeIdStr, targetFolder);
    }
  };

  const handleDragCancel = () => {
    setActiveId(null);
    setDragOverFolderId(null);
  };

  const activeDoc = activeId
    ? documents.find((d) => d.id === activeId)
    : null;
  const activeFolder = activeId
    ? folders.find((f) => f.id === activeId)
    : null;

  return (
    <div>
      <div className="sb-title">Documents</div>
      <div className="doc-list">
        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          <SortableContext
            items={rootOrder}
            strategy={verticalListSortingStrategy}
          >
            {rootOrder.map((id) => {
              const folder = folders.find((f) => f.id === id);
              if (folder) {
                return (
                  <FolderItem
                    key={folder.id}
                    folder={folder}
                    docIds={folderOrders[folder.id] ?? []}
                    isDragOverFolder={dragOverFolderId === folder.id}
                  />
                );
              }

              const doc = documents.find((d) => d.id === id);
              if (doc) {
                return (
                  <SortableDocItem
                    key={doc.id}
                    id={doc.id}
                    title={doc.title}
                    folderId={null}
                  />
                );
              }

              return null;
            })}
          </SortableContext>

          <DragOverlay>
            {activeDoc ? (
              <div className="doc-item dragging-overlay">
                <svg className="doc-item-icon" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M3 1h7l4 4v10H3V1zm7 1v3h3L10 2z" />
                </svg>
                <span className="doc-item-title">{activeDoc.title}</span>
              </div>
            ) : activeFolder ? (
              <div className="folder-header dragging-overlay">
                <svg className="folder-icon" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M1 3h5l2 2h7v9H1V3zm1 1v9h12V6H7.5L5.5 4H2z" />
                </svg>
                <span className="folder-name">{activeFolder.name}</span>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        <button className="doc-new-btn" onClick={() => createDocument()}>
          <span>+</span>
          <span>New Document</span>
        </button>
        <button className="doc-new-btn doc-new-folder-btn" onClick={() => createFolder()}>
          <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
            <path d="M1 3h5l2 2h7v9H1V3zm1 1v9h12V6H7.5L5.5 4H2z" />
          </svg>
          <span>New Folder</span>
        </button>
      </div>
    </div>
  );
}
