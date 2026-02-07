import { useEffect, useRef } from 'react';
import { Topbar } from '@/components/Layout/Topbar';
import { Sidebar } from '@/components/Layout/Sidebar';
import { AnimatedOutlet } from '@/components/Layout/AnimatedOutlet';
import { useSettingsStore } from '@/stores/settingsStore';
import { useDocumentStore } from '@/stores/documentStore';

export function AppLayout() {
  const sidebarCollapsed = useSettingsStore((s) => s.sidebarCollapsed);
  const initializeFromServer = useDocumentStore((s) => s.initializeFromServer);
  const syncInitialised = useRef(false);

  useEffect(() => {
    if (syncInitialised.current) return;
    syncInitialised.current = true;
    initializeFromServer();
  }, [initializeFromServer]);

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
