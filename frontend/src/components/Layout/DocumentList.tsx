import { useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  KeyboardSensor,
  useDroppable,
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
  // First check for pointer-within collisions (folder drop targets + root zone)
  const pointerCollisions = pointerWithin(args);

  // Prioritize folder droppables
  const folderDropTarget = pointerCollisions.find((c) =>
    String(c.id).startsWith('droppable-')
  );
  if (folderDropTarget) {
    return [folderDropTarget];
  }

  // Check for root drop zone
  const rootZone = pointerCollisions.find((c) => c.id === 'root-drop-zone');

  // Use closestCenter among root items for positioning
  const centerCollisions = closestCenter(args);

  // If pointer is in root zone but closestCenter found something, use that for ordering
  if (rootZone && centerCollisions.length > 0) {
    return centerCollisions;
  }

  // If pointer is in root zone but nothing from closestCenter, return root zone
  if (rootZone) {
    return [rootZone];
  }

  return centerCollisions;
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

  // Root drop zone — allows dragging docs back to root even when only folders exist
  const { setNodeRef: setRootDropRef } = useDroppable({
    id: 'root-drop-zone',
    data: { type: 'root' },
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor)
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const handleDragOver = (event: DragOverEvent) => {
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
    const overData = over.data.current as { type: string; folderId?: string | null } | undefined;

    // Folder reorder in root
    if (activeData?.type === 'folder') {
      if (activeIdStr !== overIdStr && rootOrder.includes(overIdStr)) {
        reorderRoot(activeIdStr, overIdStr);
      }
      return;
    }

    // Only handle document drags from here
    if (activeData?.type !== 'document') return;

    const docFolderId = activeData.folderId ?? null;

    // Dropped on a folder's droppable zone → move INTO that folder
    if (overIdStr.startsWith('droppable-')) {
      const targetFolderId = overIdStr.replace('droppable-', '');
      if (docFolderId !== targetFolderId) {
        moveDocumentToFolder(activeIdStr, targetFolderId);
      }
      return;
    }

    // Dropped on root drop zone with no specific target → move to root
    if (overIdStr === 'root-drop-zone') {
      if (docFolderId) {
        moveDocumentToFolder(activeIdStr, null);
      }
      return;
    }

    if (activeIdStr === overIdStr) return;

    // Determine where the over target lives
    const isOverInRoot = rootOrder.includes(overIdStr);
    const overFolderId = overData?.folderId ?? null;

    if (docFolderId && isOverInRoot) {
      // Doc is in a folder, dropped on a root-level item → move to root & reorder
      moveDocumentToFolder(activeIdStr, null);
      reorderRoot(activeIdStr, overIdStr);
    } else if (!docFolderId && isOverInRoot) {
      // Both in root → simple reorder
      reorderRoot(activeIdStr, overIdStr);
    } else if (docFolderId && overFolderId && docFolderId === overFolderId) {
      // Reorder within the same folder
      reorderInFolder(docFolderId, activeIdStr, overIdStr);
    } else if (overFolderId && docFolderId !== overFolderId) {
      // Cross-folder move
      moveDocumentToFolder(activeIdStr, overFolderId);
    } else if (!docFolderId && overFolderId) {
      // Root doc dropped on a doc inside a folder → move into that folder
      moveDocumentToFolder(activeIdStr, overFolderId);
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
      <div className="doc-list" ref={setRootDropRef}>
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
