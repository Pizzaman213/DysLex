interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Card({ title, children, className = '', ...rest }: CardProps) {
  return (
    <div className={`card ${className}`} {...rest}>
      {title && <h3 className="card-title">{title}</h3>}
      <div className="card-content">{children}</div>
    </div>
  );
}
