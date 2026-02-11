import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary';

function BombComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Boom');
  return <div>All good</div>;
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress React's noisy error boundary logging during tests
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <BombComponent shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('All good')).toBeTruthy();
  });

  it('renders fallback UI when a child throws', () => {
    render(
      <ErrorBoundary>
        <BombComponent shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.getByText('Something unexpected happened')).toBeTruthy();
    expect(screen.getByText('Try Again')).toBeTruthy();
    expect(screen.getByText('Go to Capture')).toBeTruthy();
  });

  it('"Try Again" resets state and re-renders children', () => {
    // First render: bomb throws. After clicking "Try Again" we
    // re-render with shouldThrow=false so it recovers.
    const { rerender } = render(
      <ErrorBoundary>
        <BombComponent shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Should show fallback
    expect(screen.getByRole('alert')).toBeTruthy();

    // Swap children to a non-throwing version, then click "Try Again"
    rerender(
      <ErrorBoundary>
        <BombComponent shouldThrow={false} />
      </ErrorBoundary>,
    );

    fireEvent.click(screen.getByText('Try Again'));
    expect(screen.getByText('All good')).toBeTruthy();
  });
});
