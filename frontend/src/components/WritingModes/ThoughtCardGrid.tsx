/**
 * Sortable grid of thought cards with drag-and-drop support.
 * Uses flex-wrap layout for responsive card arrangement.
 */

import { DndContext, closestCenter, DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, rectSortingStrategy } from '@dnd-kit/sortable';
import { useCaptureStore } from '../../stores/captureStore';
import { ThoughtCard } from './ThoughtCard';

interface ThoughtCardGridProps {
  isLoading?: boolean;
}

export function ThoughtCardGrid({ isLoading }: ThoughtCardGridProps) {
  const cards = useCaptureStore((s) => s.cards);
  const reorderCards = useCaptureStore((s) => s.reorderCards);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = cards.findIndex((card) => card.id === active.id);
      const newIndex = cards.findIndex((card) => card.id === over.id);

      if (oldIndex !== -1 && newIndex !== -1) {
        reorderCards(oldIndex, newIndex);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="thought-card-grid" role="status">
        <div className="thought-card-skeleton" aria-label="Loading ideas...">
          <div className="skeleton-header" />
          <div className="skeleton-title" />
          <div className="skeleton-body" />
        </div>
        <div className="thought-card-skeleton" aria-hidden="true">
          <div className="skeleton-header" />
          <div className="skeleton-title" />
          <div className="skeleton-body" />
        </div>
        <div className="thought-card-skeleton" aria-hidden="true">
          <div className="skeleton-header" />
          <div className="skeleton-title" />
          <div className="skeleton-body" />
        </div>
      </div>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="thought-card-grid-empty" role="status">
        <p>Your ideas will appear here as cards.</p>
        <p className="thought-card-grid-hint">Drag cards to reorder, edit them, or remove ones you don't need.</p>
      </div>
    );
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={cards.map((c) => c.id)} strategy={rectSortingStrategy}>
        <div className="thought-card-grid" role="list">
          {cards.map((card, index) => (
            <ThoughtCard
              key={card.id}
              id={card.id}
              title={card.title}
              body={card.body}
              index={index}
            />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
