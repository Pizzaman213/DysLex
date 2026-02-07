import { useEffect, useRef } from 'react';
import { EdgeRelationship } from './types';

const RELATIONSHIP_OPTIONS: Array<{
  value: EdgeRelationship | null;
  label: string;
  color: string;
}> = [
  { value: 'supports', label: 'Supports', color: 'var(--green)' },
  { value: 'contradicts', label: 'Contradicts', color: 'var(--error, #c44)' },
  { value: 'leads_to', label: 'Leads to', color: 'var(--blue)' },
  { value: 'example_of', label: 'Example of', color: 'var(--yellow)' },
  { value: 'related_to', label: 'Related to', color: 'var(--border2, rgba(45,42,36,.15))' },
  { value: null, label: 'No label', color: 'var(--border2, rgba(45,42,36,.15))' },
];

interface EdgeLabelPickerProps {
  position: { x: number; y: number };
  currentRelationship: EdgeRelationship | null;
  onSelect: (relationship: EdgeRelationship | null) => void;
  onClose: () => void;
}

export function EdgeLabelPicker({ position, currentRelationship, onSelect, onClose }: EdgeLabelPickerProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    // Delay listener to avoid closing immediately from the creating click
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscape);
    }, 0);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="edge-label-picker"
      style={{
        position: 'absolute',
        left: position.x,
        top: position.y,
        transform: 'translate(-50%, -50%)',
        zIndex: 1000,
      }}
      role="listbox"
      aria-label="Select edge relationship"
    >
      {RELATIONSHIP_OPTIONS.map((option) => (
        <button
          key={option.label}
          type="button"
          className={`edge-label-option${currentRelationship === option.value ? ' edge-label-option-active' : ''}`}
          onClick={() => onSelect(option.value)}
          role="option"
          aria-selected={currentRelationship === option.value}
        >
          <span
            className="edge-label-option-dot"
            style={{ background: option.color }}
          />
          {option.label}
        </button>
      ))}
    </div>
  );
}
