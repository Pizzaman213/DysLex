import { useSettingsStore } from '@/stores/settingsStore';
import type { Theme } from '@/types';

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: 'cream', label: 'Cream' },
  { value: 'night', label: 'Night' },
  { value: 'blue-tint', label: 'Blue Tint' },
];

export function ThemeSwitcher() {
  const { theme, setTheme } = useSettingsStore();

  return (
    <select
      className="theme-switcher"
      value={theme}
      onChange={(e) => setTheme(e.target.value as Theme)}
      aria-label="Select theme"
    >
      {THEME_OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
