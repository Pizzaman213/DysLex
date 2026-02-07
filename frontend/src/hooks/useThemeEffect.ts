import { useEffect } from 'react';
import { useSettingsStore } from '@/stores/settingsStore';

export function useThemeEffect() {
  const theme = useSettingsStore((s) => s.theme);

  useEffect(() => {
    if (theme === 'cream') {
      delete document.documentElement.dataset.theme;
    } else {
      document.documentElement.dataset.theme = theme;
    }
  }, [theme]);
}
