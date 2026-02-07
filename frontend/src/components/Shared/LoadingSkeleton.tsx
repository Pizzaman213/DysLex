interface LoadingSkeletonProps {
  width?: string;
  height?: string;
  variant?: 'text' | 'card' | 'circular';
  count?: number;
}

export function LoadingSkeleton({
  width = '100%',
  height = '1rem',
  variant = 'text',
  count = 1
}: LoadingSkeletonProps) {
  const skeletons = Array.from({ length: count }, (_, i) => (
    <div
      key={i}
      className={`skeleton skeleton--${variant}`}
      style={{ width, height }}
      aria-hidden="true"
    />
  ));

  return (
    <div className="skeleton-container" role="status" aria-label="Loading content">
      {skeletons}
    </div>
  );
}
