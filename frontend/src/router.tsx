import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/Layout/AppLayout';
import { CapturePage } from '@/modes/CapturePage';
import { MindMapPage } from '@/modes/MindMapPage';
import { DraftPage } from '@/modes/DraftPage';
import { PolishPage } from '@/modes/PolishPage';
import { ProgressPage } from '@/modes/ProgressPage';
import { SettingsPage } from '@/modes/SettingsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/draft" replace /> },
      { path: 'capture', element: <CapturePage /> },
      { path: 'mindmap', element: <MindMapPage /> },
      { path: 'draft', element: <DraftPage /> },
      { path: 'polish', element: <PolishPage /> },
      { path: 'progress', element: <ProgressPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
]);
