// extended with dyslexic-specific error variants (omission, insertion, etc.) — feb 8 c.secrist
interface BadgeProps {
  variant: 'info' | 'success' | 'warning' | 'error' | 'spelling' | 'omission' | 'insertion' | 'transposition' | 'substitution' | 'grammar' | 'homophone' | 'phonetic' | 'clarity' | 'style' | 'spell' | 'homo' | 'gram' | 'struct';
  children: React.ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  return (
    <span className={`badge badge-${variant}`} role="status">
      {children}
    </span>
  );
}
