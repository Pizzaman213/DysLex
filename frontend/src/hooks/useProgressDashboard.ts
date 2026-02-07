/**
 * Custom hook for fetching progress dashboard data
 */

import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ProgressDashboardResponse } from '../types/progress';

interface UseProgressDashboardResult {
  data: ProgressDashboardResponse | null;
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

export function useProgressDashboard(weeks: number = 12): UseProgressDashboardResult {
  const [data, setData] = useState<ProgressDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchDashboard = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await api.getProgressDashboard(weeks);
      setData(response.data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch dashboard'));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [weeks]);

  return {
    data,
    isLoading,
    error,
    refresh: fetchDashboard,
  };
}
