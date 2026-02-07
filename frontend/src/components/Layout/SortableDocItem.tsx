import { useState, useRef, useEffect, useCallback } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useDocumentStore } from '@/stores/documentStore';
import { ContextMenu } from './ContextMenu';
import type { ContextMenuItem } from './ContextMenu';

interface SortableDocItemProps {
  id: string;
  title: string;
  folderId: string | null;
}

export function SortableDocItem({ id, title, folderId }: SortableDocItemProps) {
  const activeDocumentId = useDocumentStore((s) => s.activeDocumentId);
  const switchDocument = useDocumentStore((s) => s.switchDocument);
  const deleteDocument = useDocumentStore((s) => s.deleteDocument);
  const updateDocumentTitle = useDocumentStore((s) => s.updateDocumentTitle);
  const documents = useDocumentStore((s) => s.documents);

  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id,
    data: { type: 'document', folderId },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    touchAction: 'none' as const,
  };

  useEffect(() => {
    if (isRenaming && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isRenaming]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY });
  }, []);

  const commitRename = () => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== title) {
      updateDocumentTitle(id, trimmed);
    }
    setIsRenaming(false);
  };

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      commitRename();
    } else if (e.key === 'Escape') {
      setIsRenaming(false);
    }
  };

  const canDelete = documents.length > 1;

  const contextMenuItems: ContextMenuItem[] = [
    {
      label: 'Rename',
      icon: (
        <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
          <path d="M12.1 1.9a1.5 1.5 0 0 1 2.1 2.1L5.6 12.6l-3.2.8.8-3.2L12.1 1.9z" />
        </svg>
      ),
      onClick: () => {
        setRenameValue(title);
        setIsRenaming(true);
      },
    },
    { label: '', onClick: () => {}, separator: true },
    {
      label: 'Delete',
      danger: true,
      icon: (
        <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
          <path d="M5 2V1h6v1h4v2H1V2h4zm1 0h4V1.5H6V2zM2 5h12l-1 10H3L2 5zm3 1v8h1V6H5zm2.5 0v8h1V6h-1zM10 6v8h1V6h-1z" />
        </svg>
      ),
      onClick: () => {
        if (canDelete) {
          deleteDocument(id);
        }
      },
    },
  ];

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        className={`doc-item ${id === activeDocumentId ? 'active' : ''} ${isDragging ? 'is-dragging' : ''}`}
        onClick={() => {
          if (!isRenaming) switchDocument(id);
        }}
        onContextMenu={handleContextMenu}
        title={title}
        {...attributes}
        {...listeners}
      >
        <span className="doc-item-grip" aria-hidden="true">⋮⋮</span>
        <svg className="doc-item-icon" viewBox="0 0 16 16" fill="currentColor">
          <path d="M3 1h7l4 4v10H3V1zm7 1v3h3L10 2z" />
        </svg>
        {isRenaming ? (
          <input
            ref={inputRef}
            className="doc-rename-input"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onBlur={commitRename}
            onKeyDown={handleRenameKeyDown}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="doc-item-title">{title}</span>
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
