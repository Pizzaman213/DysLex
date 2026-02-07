import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('has role="status"', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('displays default label "Loading..."', () => {
    render(<LoadingSpinner />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays a custom label when provided', () => {
    render(<LoadingSpinner label="Saving document..." />);
    expect(screen.getByText('Saving document...')).toBeInTheDocument();
  });
});
