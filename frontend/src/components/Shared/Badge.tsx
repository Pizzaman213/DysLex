interface BadgeProps {
  variant: 'info' | 'success' | 'warning' | 'error';
  children: React.ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  return (
    <span className={`badge badge-${variant}`} role="status">
      {children}
    </span>
  );
}
