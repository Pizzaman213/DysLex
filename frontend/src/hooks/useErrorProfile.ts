import { useState, useEffect } from 'react';
import { api } from '../services/api';

interface Pattern {
  id: string;
  description: string;
  mastered: boolean;
  progress: number;
}

interface Achievement {
  id: string;
  name: string;
  icon: string;
  earnedAt: string;
}

interface ErrorProfile {
  userId: string;
  overallScore: number;
  topPatterns: Pattern[];
  achievements: Achievement[];
  confusionPairs: Array<{ word1: string; word2: string; frequency: number }>;
  lastUpdated: string;
}

export function useErrorProfile() {
  const [profile, setProfile] = useState<ErrorProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setIsLoading(true);
        const data = await api.getErrorProfile();
        setProfile(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch profile'));
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfile();
  }, []);

  const refreshProfile = async () => {
    try {
      const data = await api.getErrorProfile();
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to refresh profile'));
    }
  };

  return {
    profile,
    isLoading,
    error,
    refreshProfile,
  };
}
