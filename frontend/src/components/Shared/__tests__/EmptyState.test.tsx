import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EmptyState } from '../EmptyState';

describe('EmptyState', () => {
  it('renders the title', () => {
    render(<EmptyState icon="📄" title="No documents" />);
    expect(screen.getByText('No documents')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(
      <EmptyState
        icon="📄"
        title="No documents"
        description="Create a new document to get started."
      />
    );
    expect(screen.getByText('Create a new document to get started.')).toBeInTheDocument();
  });

  it('renders action button and calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        icon="📄"
        title="No documents"
        action={{ label: 'New Document', onClick }}
      />
    );
    const btn = screen.getByRole('button', { name: 'New Document' });
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('does not render action button when action is not provided', () => {
    render(<EmptyState icon="📄" title="No documents" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
