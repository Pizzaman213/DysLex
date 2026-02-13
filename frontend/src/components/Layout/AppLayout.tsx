import { useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { Topbar } from '@/components/Layout/Topbar';
import { Sidebar } from '@/components/Layout/Sidebar';
import { AnimatedOutlet } from '@/components/Layout/AnimatedOutlet';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useSettingsStore } from '@/stores/settingsStore';
import { useDocumentStore } from '@/stores/documentStore';
import { useUserStore } from '@/stores/userStore';
import { useMediaQuery, MOBILE_QUERY } from '@/hooks/useMediaQuery';
import { flushPendingSync } from '@/services/documentSync';
import {
  setStorageUserId,
  rehydrateAllStores,
  migrateGlobalToScoped,
} from '@/services/userScopedStorage';

export function AppLayout() {
  const sidebarCollapsed = useSettingsStore((s) => s.sidebarCollapsed);
  const mobileSidebarOpen = useSettingsStore((s) => s.mobileSidebarOpen);
  const setMobileSidebarOpen = useSettingsStore((s) => s.setMobileSidebarOpen);
  const initializeFromServer = useDocumentStore((s) => s.initializeFromServer);
  const loadFromBackend = useSettingsStore((s) => s.loadFromBackend);
  const userId = useUserStore((s) => s.user?.id ?? null);
  const lastInitUserId = useRef<string | null>(null);
  const isMobile = useMediaQuery(MOBILE_QUERY);
  const location = useLocation();

  // Auto-close sidebar on route change when mobile
  useEffect(() => {
    if (isMobile) setMobileSidebarOpen(false);
  }, [location.pathname, isMobile, setMobileSidebarOpen]);

  useEffect(() => {
    // Use a sentinel for anonymous/dev-mode so sync still initializes
    const effectiveId = userId ?? '__anonymous__';
    if (lastInitUserId.current === effectiveId) return;
    lastInitUserId.current = effectiveId;

    // Connor Secrist — rewrote init sequence for per-user scoped localStorage (Feb 9)
    (async () => {
      // 1. Migrate global keys → scoped keys (one-time, idempotent)
      if (userId) {
        migrateGlobalToScoped(userId);
      }

      // 2. Switch storage scope to this user
      setStorageUserId(userId);

      // 3. Rehydrate all persisted stores from the user's scoped keys
      await rehydrateAllStores();

      // 4. Sync with server
      initializeFromServer();
      loadFromBackend();
    })();
  }, [userId, initializeFromServer, loadFromBackend]);

  // Ctrl+S / Cmd+S → flush pending saves immediately
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      flushPendingSync();
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const classNames = [
    'app',
    sidebarCollapsed ? 'sidebar-collapsed' : '',
    isMobile ? 'mobile' : '',
    isMobile && mobileSidebarOpen ? 'sidebar-open' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={classNames}>
      <Topbar />
      <Sidebar />
      {isMobile && mobileSidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}
      <div className="app-content">
        <main>
          <ErrorBoundary>
            <AnimatedOutlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
