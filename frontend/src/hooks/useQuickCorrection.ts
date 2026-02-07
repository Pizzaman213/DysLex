import { useState, useCallback, useEffect } from 'react';
import { runLocalCorrection, loadModel, getModelState } from '@/services/onnxModel';
import { initUserDictionary, stopUserDictionary } from '@/services/userCorrectionDict';
import type { Correction } from '@/types/api';

export function useQuickCorrection(userId?: string) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Preload model on mount
  useEffect(() => {
    loadModel()
      .then(() => {
        setIsLoading(false);
        console.log('[Quick Correction] Model loaded successfully');
      })
      .catch(err => {
        setError(err.message);
        setIsLoading(false);
        console.error('[Quick Correction] Failed to load model:', err);
      });
  }, []);

  // Initialize user-specific correction dictionary when userId is available
  useEffect(() => {
    if (userId) {
      initUserDictionary(userId).catch(err => {
        console.warn('[Quick Correction] Failed to load user dictionary:', err);
      });
    }
    return () => {
      stopUserDictionary();
    };
  }, [userId]);

  const correct = useCallback(async (text: string): Promise<Correction[]> => {
    try {
      const localCorrections = await runLocalCorrection(text);

      // Convert LocalCorrection to Correction format
      return localCorrections.map(c => ({
        original: c.original,
        suggested: c.correction,
        type: 'spelling' as const,
        start: c.position.start,
        end: c.position.end,
        confidence: c.confidence,
      }));
    } catch (err) {
      console.error('[Quick Correction] Correction failed:', err);
      return [];
    }
  }, []);

  return {
    correct,
    isLoading,
    error,
    modelState: getModelState(),
  };
}
