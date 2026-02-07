import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

interface TooltipProps {
  isOpen: boolean;
  anchorRect: DOMRect | null;
  onClose: () => void;
  children: React.ReactNode;
}

export function Tooltip({ isOpen, anchorRect, onClose, children }: TooltipProps) {
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !anchorRect) return null;

  // Calculate position - prefer below, flip above if not enough space
  const viewportHeight = window.innerHeight;
  const spaceBelow = viewportHeight - anchorRect.bottom;
  const spaceAbove = anchorRect.top;
  const tooltipHeight = 200; // Estimated max height

  const shouldFlipAbove = spaceBelow < tooltipHeight && spaceAbove > spaceBelow;

  const style: React.CSSProperties = {
    position: 'fixed',
    left: `${anchorRect.left}px`,
    top: shouldFlipAbove
      ? `${anchorRect.top - 8}px`
      : `${anchorRect.bottom + 8}px`,
    transform: shouldFlipAbove ? 'translateY(-100%)' : 'none',
    zIndex: 1000,
  };

  return createPortal(
    <div
      ref={tooltipRef}
      className="tooltip"
      style={style}
      role="tooltip"
      aria-live="polite"
    >
      {children}
    </div>,
    document.body
  );
}
