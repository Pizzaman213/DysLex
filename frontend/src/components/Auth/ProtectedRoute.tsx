import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useUserStore } from '@/stores/userStore';
import { getAuthToken } from '@/services/api';

export function ProtectedRoute() {
  const { isAuthenticated } = useUserStore();
  const location = useLocation();

  if (!isAuthenticated && !getAuthToken()) {
    return <Navigate to="/" state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
