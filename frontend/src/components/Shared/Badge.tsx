interface BadgeProps {
  variant: 'info' | 'success' | 'warning' | 'error' | 'spelling' | 'grammar' | 'homophone' | 'clarity' | 'style' | 'spell' | 'homo' | 'gram' | 'struct';
  children: React.ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  return (
    <span className={`badge badge-${variant}`} role="status">
      {children}
    </span>
  );
}
