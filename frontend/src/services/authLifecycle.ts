/**
 * Central logout / login lifecycle orchestrator.
 *
 * Calling performLogout() ensures every per-user store is reset so that
 * the next user who logs in starts with a clean slate — no data leaks
 * between accounts.
 */

import { setAuthToken } from '@/services/api';
import { flushPendingSync } from '@/services/documentSync';
import { useUserStore } from '@/stores/userStore';
import { useDocumentStore } from '@/stores/documentStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useSessionStore } from '@/stores/sessionStore';
import { useMindMapStore } from '@/stores/mindMapStore';
import { useCaptureStore } from '@/stores/captureStore';
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

  // 4. Reset every per-user store to defaults
  useDocumentStore.getState().resetDocuments();
  useSettingsStore.getState().resetSettings();
  useSessionStore.getState().endSession();
  useMindMapStore.getState().resetMindMap();
  useCaptureStore.getState().reset();

  // Editor store: clear content + corrections
  const editor = useEditorStore.getState();
  editor.setContent('');
  editor.clearCorrections();

  usePolishStore.getState().clearSuggestions();
  useScaffoldStore.getState().clearScaffold();
  useCoachStore.getState().clearMessages();
}
