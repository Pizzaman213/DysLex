import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useUserStore } from '@/stores/userStore';
import { getAuthToken } from '@/services/api';

export function ProtectedRoute() {
  const { isAuthenticated } = useUserStore();
  const location = useLocation();

  // In dev mode, allow unauthenticated access (matches backend demo user behavior)
  if (import.meta.env.DEV) {
    return <Outlet />;
  }

  if (!isAuthenticated && !getAuthToken()) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
