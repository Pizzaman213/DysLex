import { Card } from './Card';

interface StatCardProps {
  icon: string;
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

export function StatCard({
  icon,
  label,
  value,
  trend,
  trendValue
}: StatCardProps) {
  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend === 'up') return '↗';
    if (trend === 'down') return '↘';
    return '→';
  };

  const getTrendClass = () => {
    if (!trend) return '';
    return `stat-trend--${trend}`;
  };

  return (
    <Card className="stat-card">
      <div className="stat-card-layout">
        <div className="stat-icon" aria-hidden="true">{icon}</div>

        <div className="stat-content">
          <div className="stat-label">{label}</div>
          <div className="stat-value">{value}</div>
          {trendValue && (
            <div className={`stat-trend ${getTrendClass()}`}>
              <span className="stat-trend-icon" aria-hidden="true">
                {getTrendIcon()}
              </span>
              <span className="stat-trend-text">{trendValue}</span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
