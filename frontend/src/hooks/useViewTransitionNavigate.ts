import { useNavigate } from 'react-router-dom';
import { useCallback } from 'react';

/**
 * Wraps useNavigate to use the View Transitions API when available.
 * Falls back to a regular navigation in unsupported browsers.
 */
export function useViewTransitionNavigate() {
  const navigate = useNavigate();

  return useCallback(
    (to: string) => {
      if (
        typeof document !== 'undefined' &&
        'startViewTransition' in document
      ) {
        (document as any).startViewTransition(() => navigate(to));
      } else {
        navigate(to);
      }
    },
    [navigate],
  );
}
