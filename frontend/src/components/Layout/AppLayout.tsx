import { Outlet } from 'react-router-dom';
import { Topbar } from '@/components/Layout/Topbar';
import { Sidebar } from '@/components/Layout/Sidebar';

export function AppLayout() {
  return (
    <div className="app">
      <Topbar />
      <Sidebar />
      <div className="app-content">
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
