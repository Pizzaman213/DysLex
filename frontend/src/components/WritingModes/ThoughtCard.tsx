/**
 * Draggable thought card component with color variants.
 */

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useCaptureStore } from '../../stores/captureStore';

const VARIANT_ICONS: Record<number, string> = {
  1: '💡',
  2: '🎯',
  3: '📝',
  4: '🔮',
  5: '⚡',
};

interface ThoughtCardProps {
  id: string;
  title: string;
  body: string;
  index?: number;
}

export function ThoughtCard({ id, title, body, index = 0 }: ThoughtCardProps) {
  const updateCard = useCaptureStore((s) => s.updateCard);
  const removeCard = useCaptureStore((s) => s.removeCard);

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  // Cycle through t1-t5 based on index
  const variant = (index % 5) + 1;

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateCard(id, { title: e.target.value });
  };

  const handleBodyChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    updateCard(id, { body: e.target.value });
  };

  const handleRemove = () => {
    if (confirm('Remove this thought card?')) {
      removeCard(id);
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`thought-card t${variant}`}
      {...attributes}
    >
      <div className="thought-card-header">
        <span className="thought-card-icon" aria-hidden="true">
          {VARIANT_ICONS[variant]}
        </span>
        <button
          className="thought-card-drag-handle"
          aria-label="Drag to reorder"
          {...listeners}
        >
          ⋮⋮
        </button>
        <button
          className="thought-card-remove"
          onClick={handleRemove}
          aria-label="Remove card"
        >
          ✕
        </button>
      </div>

      <input
        className="thought-card-title"
        value={title}
        onChange={handleTitleChange}
        placeholder="Idea title..."
        aria-label="Card title"
      />

      <textarea
        className="thought-card-body"
        value={body}
        onChange={handleBodyChange}
        placeholder="Idea details..."
        aria-label="Card body"
        rows={3}
      />
    </div>
  );
}
