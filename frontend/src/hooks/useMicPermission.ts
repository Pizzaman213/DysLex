/**
 * Hook for tracking microphone permission state.
 *
 * Uses navigator.permissions.query as the source of truth and caches
 * the result in the settings store (localStorage) so the UI can respond
 * instantly on subsequent visits.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useSettingsStore } from '../stores/settingsStore';
import type { MicPermission } from '../types';

interface UseMicPermissionReturn {
  status: MicPermission;
  isDenied: boolean;
  isGranted: boolean;
  helpMessage: string | null;
  checkPermission: () => Promise<MicPermission>;
  recordGranted: () => void;
  recordDenied: () => void;
}

export function useMicPermission(): UseMicPermissionReturn {
  const status = useSettingsStore((s) => s.micPermission);
  const setMicPermission = useSettingsStore((s) => s.setMicPermission);
  const permStatusRef = useRef<PermissionStatus | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function queryPermission() {
      try {
        const permStatus = await navigator.permissions.query(
          { name: 'microphone' as PermissionName }
        );
        if (!cancelled) {
          permStatusRef.current = permStatus;
          setMicPermission(permStatus.state as MicPermission);

          permStatus.onchange = () => {
            setMicPermission(permStatus.state as MicPermission);
          };
        }
      } catch {
        // Permissions API not supported (e.g. Firefox for microphone)
        // Leave as cached value — recordGranted/recordDenied will update after getUserMedia
      }
    }

    queryPermission();

    return () => {
      cancelled = true;
      if (permStatusRef.current) {
        permStatusRef.current.onchange = null;
      }
    };
  }, [setMicPermission]);

  const checkPermission = useCallback(async (): Promise<MicPermission> => {
    try {
      const permStatus = await navigator.permissions.query(
        { name: 'microphone' as PermissionName }
      );
      const state = permStatus.state as MicPermission;
      setMicPermission(state);
      return state;
    } catch {
      return status;
    }
  }, [status, setMicPermission]);

  const recordGranted = useCallback(() => {
    setMicPermission('granted');
  }, [setMicPermission]);

  const recordDenied = useCallback(() => {
    setMicPermission('denied');
  }, [setMicPermission]);

  const isDenied = status === 'denied';
  const isGranted = status === 'granted';

  const helpMessage = isDenied
    ? 'Microphone access is blocked. To re-enable, click the lock icon in your browser\'s address bar and allow microphone access, then reload the page.'
    : null;

  return {
    status,
    isDenied,
    isGranted,
    helpMessage,
    checkPermission,
    recordGranted,
    recordDenied,
  };
}
