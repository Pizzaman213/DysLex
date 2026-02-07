/**
 * User Correction Dictionary Service
 *
 * Fetches the user's personalized misspelling -> correction map from the backend
 * (built automatically from passive learning data) and feeds it to the ONNX model.
 *
 * The dictionary is refreshed periodically so corrections improve as the user writes.
 */

import { api } from './api';
import { updateUserDictionary } from './onnxModel';

let refreshInterval: ReturnType<typeof setInterval> | null = null;
let currentUserId: string | null = null;
let lastFetchedCount = 0;

const REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Initialize the user correction dictionary.
 * Fetches the user's error patterns from the backend and updates the ONNX model.
 */
export async function initUserDictionary(userId: string): Promise<void> {
  currentUserId = userId;

  // Fetch immediately
  await fetchAndUpdate(userId);

  // Set up periodic refresh
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  refreshInterval = setInterval(() => {
    if (currentUserId) {
      fetchAndUpdate(currentUserId).catch((err) => {
        console.warn('[UserDict] Periodic refresh failed:', err);
      });
    }
  }, REFRESH_INTERVAL_MS);
}

/**
 * Stop the periodic refresh.
 */
export function stopUserDictionary(): void {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
  currentUserId = null;
}

/**
 * Force a refresh of the user dictionary (e.g., after applying a correction).
 */
export async function refreshUserDictionary(): Promise<void> {
  if (currentUserId) {
    await fetchAndUpdate(currentUserId);
  }
}

/**
 * Get the number of user-specific correction entries.
 */
export function getUserDictSize(): number {
  return lastFetchedCount;
}

/**
 * Fetch the user's correction dictionary from the backend and update the ONNX model.
 */
async function fetchAndUpdate(userId: string): Promise<void> {
  try {
    const response = await api.getUserCorrectionDict(userId);
    const correctionDict: Record<string, string> = response.data.correction_dict;
    lastFetchedCount = response.data.count;

    updateUserDictionary(correctionDict);

    if (lastFetchedCount > 0) {
      console.log(`[UserDict] Loaded ${lastFetchedCount} personalized corrections for user`);
    }
  } catch (err) {
    // Silently fail — base dictionary still works
    console.warn('[UserDict] Failed to fetch user correction dict:', err);
  }
}
