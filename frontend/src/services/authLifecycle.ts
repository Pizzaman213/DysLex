/**
 * Central logout / login lifecycle orchestrator.
 *
 * On logout, switches the storage scope to '__anonymous__' and rehydrates
 * all persisted stores from the anonymous scope. The previous user's data
 * stays safe in their scoped localStorage keys (e.g. `dyslex-documents::userId`).
 *
 * Refactored for user-scoped storage — Connor Secrist, Feb 9 2026
 */

import { setAuthToken } from '@/services/api';
import { flushPendingSync } from '@/services/documentSync';
import { setStorageUserId, rehydrateAllStores } from '@/services/userScopedStorage';
import { useUserStore } from '@/stores/userStore';
import { useEditorStore } from '@/stores/editorStore';
import { usePolishStore } from '@/stores/polishStore';
import { useScaffoldStore } from '@/stores/scaffoldStore';
import { useCoachStore } from '@/stores/coachStore';

export async function performLogout(): Promise<void> {
  // 1. Flush any pending debounced saves before tearing down
  try {
    await flushPendingSync();
  } catch {
    // Flush is best-effort — logout must always complete
  }

  // 2. Clear auth token from localStorage / axios headers
  setAuthToken(null);

  // 3. Clear user identity
  useUserStore.getState().logout();

  // 4. Switch storage scope to anonymous and rehydrate persisted stores
  //    (loads anonymous/empty data — previous user's data stays in scoped keys)
  setStorageUserId(null);
  await rehydrateAllStores();

  // 5. Reset in-memory-only stores (not persisted, no scoping needed)
  const editor = useEditorStore.getState();
  editor.setContent('');
  editor.clearCorrections();

  usePolishStore.getState().clearSuggestions();
  useScaffoldStore.getState().clearScaffold();
  useCoachStore.getState().clearMessages();
}
