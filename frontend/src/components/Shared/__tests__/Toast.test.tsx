import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Toast } from '../Toast';
import type { Toast as ToastType } from '@/hooks/useToast';

function makeToast(overrides: Partial<ToastType> = {}): ToastType {
  return {
    id: 'toast-1',
    message: 'Something happened',
    type: 'info',
    ...overrides,
  };
}

describe('Toast', () => {
  it('renders message text', () => {
    render(<Toast toast={makeToast()} onDismiss={vi.fn()} />);
    expect(screen.getByText('Something happened')).toBeInTheDocument();
  });

  it('calls onDismiss with the toast id when dismiss button is clicked', () => {
    const onDismiss = vi.fn();
    render(<Toast toast={makeToast({ id: 'abc-123' })} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button', { name: /dismiss notification/i }));
    expect(onDismiss).toHaveBeenCalledWith('abc-123');
  });

  it('has role="status"', () => {
    render(<Toast toast={makeToast()} onDismiss={vi.fn()} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders checkmark icon for success type', () => {
    const { container } = render(
      <Toast toast={makeToast({ type: 'success' })} onDismiss={vi.fn()} />
    );
    const icon = container.querySelector('.toast__icon');
    expect(icon).toHaveTextContent('✓');
  });

  it('renders action button when action prop exists and calls onClick', () => {
    const onClick = vi.fn();
    render(
      <Toast
        toast={makeToast({ action: { label: 'Undo', onClick } })}
        onDismiss={vi.fn()}
      />
    );
    const actionBtn = screen.getByRole('button', { name: 'Undo' });
    expect(actionBtn).toBeInTheDocument();
    fireEvent.click(actionBtn);
    expect(onClick).toHaveBeenCalledOnce();
  });
});
