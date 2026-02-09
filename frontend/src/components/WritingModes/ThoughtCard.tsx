/**
 * Draggable thought card component with color variants and expandable sub-ideas.
 */

import { useState } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useCaptureStore, SubIdea } from '../../stores/captureStore';

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
  sub_ideas?: SubIdea[];
  index?: number;
}

export function ThoughtCard({ id, title, body, sub_ideas = [], index = 0 }: ThoughtCardProps) {
  const updateCard = useCaptureStore((s) => s.updateCard);
  const removeCard = useCaptureStore((s) => s.removeCard);
  const updateSubIdea = useCaptureStore((s) => s.updateSubIdea);
  const removeSubIdea = useCaptureStore((s) => s.removeSubIdea);
  const addSubIdea = useCaptureStore((s) => s.addSubIdea);

  const [subsExpanded, setSubsExpanded] = useState(false);

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

      {/* Sub-ideas expandable section */}
      {sub_ideas.length > 0 && (
        <>
          <button
            className="thought-card-subs-toggle"
            onClick={() => setSubsExpanded(!subsExpanded)}
            aria-expanded={subsExpanded}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              style={{ transform: subsExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 150ms' }}
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
            {sub_ideas.length} detail{sub_ideas.length !== 1 ? 's' : ''}
          </button>

          {subsExpanded && (
            <div className="thought-card-subs">
              {sub_ideas.map((sub) => (
                <div key={sub.id} className="thought-card-sub">
                  <input
                    className="thought-card-sub-title"
                    value={sub.title}
                    onChange={(e) => updateSubIdea(id, sub.id, { title: e.target.value })}
                    placeholder="Sub-idea..."
                    aria-label="Sub-idea title"
                  />
                  <button
                    className="thought-card-sub-remove"
                    onClick={() => removeSubIdea(id, sub.id)}
                    aria-label="Remove sub-idea"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                className="thought-card-sub-add"
                onClick={() => addSubIdea(id)}
                aria-label="Add sub-idea"
              >
                +
              </button>
            </div>
          )}
        </>
      )}

      {/* Show add button even when no sub-ideas exist (collapsed state) */}
      {sub_ideas.length === 0 && (
        <button
          className="thought-card-sub-add"
          onClick={() => addSubIdea(id)}
          aria-label="Add sub-idea"
        >
          + Add detail
        </button>
      )}
    </div>
  );
}
