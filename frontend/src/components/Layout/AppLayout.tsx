import { useEffect, useRef, useCallback } from 'react';
import { Topbar } from '@/components/Layout/Topbar';
import { Sidebar } from '@/components/Layout/Sidebar';
import { AnimatedOutlet } from '@/components/Layout/AnimatedOutlet';
import { useSettingsStore } from '@/stores/settingsStore';
import { useDocumentStore } from '@/stores/documentStore';
import { useUserStore } from '@/stores/userStore';
import { flushPendingSync } from '@/services/documentSync';

export function AppLayout() {
  const sidebarCollapsed = useSettingsStore((s) => s.sidebarCollapsed);
  const initializeFromServer = useDocumentStore((s) => s.initializeFromServer);
  const loadFromBackend = useSettingsStore((s) => s.loadFromBackend);
  const userId = useUserStore((s) => s.user?.id ?? null);
  const lastInitUserId = useRef<string | null>(null);

  useEffect(() => {
    // Use a sentinel for anonymous/dev-mode so sync still initializes
    const effectiveId = userId ?? '__anonymous__';
    if (lastInitUserId.current === effectiveId) return;
    lastInitUserId.current = effectiveId;

    initializeFromServer();
    loadFromBackend();
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

  return (
    <div className={`app ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <Topbar />
      <Sidebar />
      <div className="app-content">
        <main>
          <AnimatedOutlet />
        </main>
      </div>
    </div>
  );
}
