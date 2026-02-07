import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useDocumentStore } from '@/stores/documentStore';

interface SortableDocItemProps {
  id: string;
  title: string;
  folderId: string | null;
}

export function SortableDocItem({ id, title, folderId }: SortableDocItemProps) {
  const activeDocumentId = useDocumentStore((s) => s.activeDocumentId);
  const switchDocument = useDocumentStore((s) => s.switchDocument);

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

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`doc-item ${id === activeDocumentId ? 'active' : ''} ${isDragging ? 'is-dragging' : ''}`}
      onClick={() => switchDocument(id)}
      title={title}
      {...attributes}
      {...listeners}
    >
      <span className="doc-item-grip" aria-hidden="true">⋮⋮</span>
      <svg className="doc-item-icon" viewBox="0 0 16 16" fill="currentColor">
        <path d="M3 1h7l4 4v10H3V1zm7 1v3h3L10 2z" />
      </svg>
      <span className="doc-item-title">{title}</span>
    </div>
  );
}
