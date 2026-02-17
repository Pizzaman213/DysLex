import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '@/components/Layout/AppLayout';
import { ProtectedRoute } from '@/components/Auth/ProtectedRoute';
import { PublicLanding } from '@/components/Auth/PublicLanding';
import { LoginPage } from '@/modes/LoginPage';
import { SignupPage } from '@/modes/SignupPage';
import { CapturePage } from '@/modes/CapturePage';
import { MindMapPage } from '@/modes/MindMapPage';
import { DraftPage } from '@/modes/DraftPage';
import { PolishPage } from '@/modes/PolishPage';
import { ProgressPage } from '@/modes/ProgressPage';
import { SettingsPage } from '@/modes/SettingsPage';

export const router = createBrowserRouter([
  // Public routes (no layout)
  { path: '/', element: <PublicLanding /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/signup', element: <SignupPage /> },

  // Protected routes (with layout)
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: '/capture', element: <CapturePage /> },
          { path: '/mindmap', element: <MindMapPage /> },
          { path: '/draft', element: <DraftPage /> },
          { path: '/polish', element: <PolishPage /> },
          { path: '/progress', element: <ProgressPage /> },
          { path: '/settings', element: <SettingsPage /> },
        ],
      },
    ],
  },
]);
