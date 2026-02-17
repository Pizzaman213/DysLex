import { Navigate } from 'react-router-dom';
import { useUserStore } from '@/stores/userStore';
import { getAuthToken } from '@/services/api';
import { LandingPage } from '@/modes/LandingPage';

export function PublicLanding() {
  const { isAuthenticated } = useUserStore();

  if (isAuthenticated || getAuthToken()) {
    return <Navigate to="/capture" replace />;
  }

  return <LandingPage />;
}
