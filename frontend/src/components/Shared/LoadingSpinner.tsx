interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export function LoadingSpinner({ size = 'md', label = 'Loading...' }: LoadingSpinnerProps) {
  const sizeClass = `spinner--${size}`;

  return (
    <div className="spinner-container" role="status" aria-live="polite">
      <div className={`spinner ${sizeClass}`} aria-hidden="true"></div>
      <span className="sr-only">{label}</span>
    </div>
  );
}
