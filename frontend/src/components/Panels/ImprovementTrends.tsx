// @ts-nocheck
/**
 * Improvement Trends component
 * Shows sparklines and trend indicators for each error type
 */

import React from 'react';
import { Sparklines, SparklinesLine } from 'react-sparklines';
import { Badge } from '../Shared/Badge';
import type { ErrorTypeImprovement } from '../../types/progress';

interface ImprovementTrendsProps {
  improvements: ErrorTypeImprovement[];
}

function formatErrorType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function getTrendBadge(trend: string, changePercent: number) {
  const absChange = Math.abs(changePercent);

  if (trend === 'improving') {
    return (
      <Badge variant="success">
        ↓ {absChange.toFixed(0)}% fewer errors
      </Badge>
    );
  }

  if (trend === 'needs_attention') {
    return (
      <Badge variant="warning">
        ↑ {absChange.toFixed(0)}% more errors
      </Badge>
    );
  }

  return (
    <Badge variant="info">
      Stable
    </Badge>
  );
}

export function ImprovementTrends({ improvements }: ImprovementTrendsProps) {
  if (improvements.length === 0) {
    return (
      <section aria-label="Improvement trends">
        <h2>Improvement Trends</h2>
        <p className="empty-state">
          Start writing to see your progress by error type!
        </p>
      </section>
    );
  }

  return (
    <section aria-label="Improvement trends">
      <h2>Improvement by Error Type</h2>
      <ul className="trends-list">
        {improvements.map((item) => (
          <li key={item.error_type} className="trend-item">
            <div className="trend-header">
              <h3>{formatErrorType(item.error_type)}</h3>
              {getTrendBadge(item.trend, item.change_percent)}
            </div>
            <div className="trend-sparkline" aria-label={`${formatErrorType(item.error_type)} trend over time`}>
              <Sparklines data={item.sparkline_data} width={100} height={20}>
                <SparklinesLine
                  color={item.trend === 'improving' ? '#4CAF50' : item.trend === 'needs_attention' ? '#FF9800' : '#2196F3'}
                  style={{ strokeWidth: 2 }}
                />
              </Sparklines>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
