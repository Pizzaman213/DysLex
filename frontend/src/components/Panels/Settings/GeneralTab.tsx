import { useSettingsStore } from '@/stores/settingsStore';
import type { Language } from '@/types';

export function GeneralTab() {
  const { language, setLanguage } = useSettingsStore();

  const languages: { value: Language; label: string }[] = [
    { value: 'en', label: 'English' },
    { value: 'es', label: 'Español' },
    { value: 'fr', label: 'Français' },
    { value: 'de', label: 'Deutsch' },
  ];

  return (
    <div className="settings-tab-content" role="tabpanel" id="general-panel" aria-labelledby="general-tab">
      <h2>General Settings</h2>

      <div className="setting-row">
        <label htmlFor="language-select">
          <span className="setting-label">Language</span>
          <span className="setting-help">Interface and correction language</span>
        </label>
        <select
          id="language-select"
          value={language}
          onChange={(e) => setLanguage(e.target.value as Language)}
          className="setting-select"
        >
          {languages.map((lang) => (
            <option key={lang.value} value={lang.value}>
              {lang.label}
            </option>
          ))}
        </select>
      </div>

      <div className="setting-info">
        <p>
          <strong>Note:</strong> User account management (name, email, password) will be added in a future update.
        </p>
      </div>
    </div>
  );
}
