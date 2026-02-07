// @ts-nocheck
/**
 * Error Frequency Charts component
 * Displays visualizations of error patterns over time
 */

import React from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '../Shared/Card';
import type { ErrorFrequencyWeek, ErrorTypeBreakdown, TopError } from '../../types/progress';

interface ErrorFrequencyChartsProps {
  errorFrequency: ErrorFrequencyWeek[];
  errorBreakdown: ErrorTypeBreakdown[];
  topErrors: TopError[];
}

export function ErrorFrequencyCharts({ errorFrequency, errorBreakdown, topErrors }: ErrorFrequencyChartsProps) {
  // Format week dates for display
  const formatWeek = (dateStr: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <section aria-label="Error frequency charts" className="error-frequency-charts">
      <h2>Error Patterns Over Time</h2>

      {/* Line Chart: Total Errors per Week */}
      <Card>
        <h3>Weekly Error Frequency</h3>
        {errorFrequency.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={errorFrequency}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis
                dataKey="week_start"
                tickFormatter={formatWeek}
                stroke="var(--text-secondary)"
              />
              <YAxis stroke="var(--text-secondary)" />
              <Tooltip
                labelFormatter={formatWeek}
                contentStyle={{
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="total_errors"
                name="Total Errors"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={{ fill: 'var(--accent)' }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="empty-state">No data available yet. Keep writing!</p>
        )}
      </Card>

      {/* Stacked Bar Chart: Error Breakdown by Type */}
      <Card>
        <h3>Error Types Breakdown</h3>
        {errorBreakdown.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={errorBreakdown}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis
                dataKey="week_start"
                tickFormatter={formatWeek}
                stroke="var(--text-secondary)"
              />
              <YAxis stroke="var(--text-secondary)" />
              <Tooltip
                labelFormatter={formatWeek}
                contentStyle={{
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                }}
              />
              <Legend />
              <Bar dataKey="spelling" stackId="a" fill="#E07B4C" name="Spelling" />
              <Bar dataKey="grammar" stackId="a" fill="#4A90E2" name="Grammar" />
              <Bar dataKey="confusion" stackId="a" fill="#F39C12" name="Confusion" />
              <Bar dataKey="phonetic" stackId="a" fill="#9B59B6" name="Phonetic" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="empty-state">No data available yet. Keep writing!</p>
        )}
      </Card>

      {/* Horizontal Bar Chart: Top Errors */}
      <Card>
        <h3>Most Frequent Corrections</h3>
        {topErrors.length > 0 ? (
          <ResponsiveContainer width="100%" height={Math.max(300, topErrors.length * 40)}>
            <BarChart data={topErrors} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis type="number" stroke="var(--text-secondary)" />
              <YAxis
                type="category"
                dataKey="original"
                width={100}
                stroke="var(--text-secondary)"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                }}
                formatter={(value: number, name: string, props: any) => [
                  `${value} times`,
                  `${props.payload.original} → ${props.payload.corrected}`,
                ]}
              />
              <Bar dataKey="frequency" fill="var(--accent)" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="empty-state">No corrections tracked yet. Keep writing!</p>
        )}
      </Card>
    </section>
  );
}
