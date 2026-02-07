import { useState, useRef, useEffect, useCallback } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useDocumentStore } from '@/stores/documentStore';
import { SortableDocItem } from './SortableDocItem';
import { ContextMenu } from './ContextMenu';
import type { ContextMenuItem } from './ContextMenu';
import type { Folder } from '@/types/document';

interface FolderItemProps {
  folder: Folder;
  docIds: string[];
  isDragOverFolder: boolean;
}

export function FolderItem({ folder, docIds, isDragOverFolder }: FolderItemProps) {
  const documents = useDocumentStore((s) => s.documents);
  const toggleFolder = useDocumentStore((s) => s.toggleFolder);
  const renameFolder = useDocumentStore((s) => s.renameFolder);
  const deleteFolder = useDocumentStore((s) => s.deleteFolder);

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(folder.name);
  const inputRef = useRef<HTMLInputElement>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);

  const {
    attributes,
    listeners,
    setNodeRef: setSortableRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: folder.id,
    data: { type: 'folder' },
  });

  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: `droppable-${folder.id}`,
    data: { type: 'folder-drop', folderId: folder.id },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    touchAction: 'none' as const,
  };

  const isDropTarget = isOver || isDragOverFolder;

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleDoubleClick = () => {
    setEditName(folder.name);
    setIsEditing(true);
  };

  const commitRename = () => {
    const trimmed = editName.trim();
    if (trimmed && trimmed !== folder.name) {
      renameFolder(folder.id, trimmed);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      commitRename();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
    }
  };

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY });
  }, []);

  const folderDocs = docIds
    .map((id) => documents.find((d) => d.id === id))
    .filter(Boolean) as typeof documents;

  const contextMenuItems: ContextMenuItem[] = [
    {
      label: 'Rename',
      icon: (
        <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
          <path d="M12.1 1.9a1.5 1.5 0 0 1 2.1 2.1L5.6 12.6l-3.2.8.8-3.2L12.1 1.9z" />
        </svg>
      ),
      onClick: () => {
        setEditName(folder.name);
        setIsEditing(true);
      },
    },
    { label: '', onClick: () => {}, separator: true },
    {
      label: 'Delete folder',
      danger: true,
      icon: (
        <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
          <path d="M5 2V1h6v1h4v2H1V2h4zm1 0h4V1.5H6V2zM2 5h12l-1 10H3L2 5zm3 1v8h1V6H5zm2.5 0v8h1V6h-1zM10 6v8h1V6h-1z" />
        </svg>
      ),
      onClick: () => {
        deleteFolder(folder.id);
      },
    },
  ];

  return (
    <>
      <div ref={setSortableRef} style={style} className="folder-item">
        <div
          ref={setDroppableRef}
          className={`folder-header ${isDropTarget ? 'drop-target' : ''} ${isDragging ? 'is-dragging' : ''}`}
          onContextMenu={handleContextMenu}
          {...attributes}
          {...listeners}
        >
          <button
            className={`folder-chevron ${folder.isExpanded ? 'expanded' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              toggleFolder(folder.id);
            }}
            aria-label={folder.isExpanded ? 'Collapse folder' : 'Expand folder'}
          >
            <svg viewBox="0 0 12 12" fill="currentColor">
              <path d="M4 2l4 4-4 4" />
            </svg>
          </button>

          <svg className="folder-icon" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1 3h5l2 2h7v9H1V3zm1 1v9h12V6H7.5L5.5 4H2z" />
          </svg>

          {isEditing ? (
            <input
              ref={inputRef}
              className="folder-name-input"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={commitRename}
              onKeyDown={handleKeyDown}
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span className="folder-name" onDoubleClick={handleDoubleClick}>
              {folder.name}
            </span>
          )}

          <span className="folder-count">{docIds.length}</span>

          <button
            className="folder-delete"
            onClick={(e) => {
              e.stopPropagation();
              deleteFolder(folder.id);
            }}
            aria-label="Delete folder"
            title="Delete folder (documents will be moved to root)"
          >
            <svg viewBox="0 0 12 12" fill="currentColor">
              <path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" strokeWidth="1.5" fill="none" />
            </svg>
          </button>
        </div>

        {folder.isExpanded && (
          <div className="folder-contents">
            <SortableContext
              items={docIds}
              strategy={verticalListSortingStrategy}
            >
              {folderDocs.map((doc) => (
                <SortableDocItem
                  key={doc.id}
                  id={doc.id}
                  title={doc.title}
                  folderId={folder.id}
                />
              ))}
            </SortableContext>
          </div>
        )}
      </div>
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenuItems}
          onClose={() => setContextMenu(null)}
        />
      )}
    </>
  );
}
