import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Dialog } from '../Dialog';

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  title: 'Test Dialog',
  children: <p>Dialog content</p>,
};

describe('Dialog', () => {
  it('returns null when isOpen is false', () => {
    const { container } = render(
      <Dialog {...defaultProps} isOpen={false} />
    );
    expect(container.innerHTML).toBe('');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders the title when open', () => {
    render(<Dialog {...defaultProps} />);
    expect(screen.getByText('Test Dialog')).toBeInTheDocument();
    expect(screen.getByText('Test Dialog').tagName).toBe('H2');
  });

  it('renders children when open', () => {
    render(<Dialog {...defaultProps} />);
    expect(screen.getByText('Dialog content')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<Dialog {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /close dialog/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('has role="dialog" and aria-modal="true"', () => {
    render(<Dialog {...defaultProps} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'dialog-title');
  });

  it('calls onClose when Escape key is pressed', () => {
    const onClose = vi.fn();
    render(<Dialog {...defaultProps} onClose={onClose} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();
  });
});
