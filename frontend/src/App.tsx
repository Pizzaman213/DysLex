import { RouterProvider } from 'react-router-dom';
import { router } from '@/router';
import { useThemeEffect } from '@/hooks/useThemeEffect';
import { useEditorTypography } from '@/hooks/useEditorTypography';

export function App() {
  useThemeEffect();
  useEditorTypography();

  return <RouterProvider router={router} />;
}
