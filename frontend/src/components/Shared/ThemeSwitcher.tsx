import { useSettingsStore } from '../../stores/settingsStore';

export function ThemeSwitcher() {
  const { theme, setTheme } = useSettingsStore();

  const toggleTheme = () => {
    setTheme(theme === 'cream' ? 'night' : 'cream');
  };

  return (
    <button
      className="theme-switcher"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'cream' ? 'night' : 'cream'} theme`}
      title={`Current: ${theme} theme`}
    >
      <span aria-hidden="true">{theme === 'cream' ? '🌙' : '☀️'}</span>
    </button>
  );
}
