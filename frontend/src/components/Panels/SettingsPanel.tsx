import { useSettingsStore } from '../../stores/settingsStore';

export function SettingsPanel() {
  const {
    theme,
    setTheme,
    font,
    setFont,
    fontSize,
    setFontSize,
    lineSpacing,
    setLineSpacing,
    voiceEnabled,
    setVoiceEnabled,
    autoCorrect,
    setAutoCorrect,
  } = useSettingsStore();

  return (
    <div className="settings-panel" role="region" aria-label="Settings">
      <h2>Settings</h2>

      <section className="settings-section">
        <h3>Appearance</h3>

        <div className="setting-row">
          <label htmlFor="theme-select">Theme</label>
          <select
            id="theme-select"
            value={theme}
            onChange={(e) => setTheme(e.target.value as 'cream' | 'night')}
          >
            <option value="cream">Cream (Light)</option>
            <option value="night">Night (Dark)</option>
          </select>
        </div>

        <div className="setting-row">
          <label htmlFor="font-select">Font</label>
          <select
            id="font-select"
            value={font}
            onChange={(e) => setFont(e.target.value)}
          >
            <option value="OpenDyslexic">OpenDyslexic</option>
            <option value="AtkinsonHyperlegible">Atkinson Hyperlegible</option>
            <option value="LexieReadable">Lexie Readable</option>
            <option value="system">System Default</option>
          </select>
        </div>

        <div className="setting-row">
          <label htmlFor="font-size">Font Size</label>
          <input
            id="font-size"
            type="range"
            min="14"
            max="24"
            value={fontSize}
            onChange={(e) => setFontSize(Number(e.target.value))}
          />
          <span className="setting-value">{fontSize}px</span>
        </div>

        <div className="setting-row">
          <label htmlFor="line-spacing">Line Spacing</label>
          <input
            id="line-spacing"
            type="range"
            min="1.2"
            max="2.0"
            step="0.1"
            value={lineSpacing}
            onChange={(e) => setLineSpacing(Number(e.target.value))}
          />
          <span className="setting-value">{lineSpacing}</span>
        </div>
      </section>

      <section className="settings-section">
        <h3>Features</h3>

        <div className="setting-row">
          <label htmlFor="voice-toggle">Voice Input</label>
          <input
            id="voice-toggle"
            type="checkbox"
            checked={voiceEnabled}
            onChange={(e) => setVoiceEnabled(e.target.checked)}
          />
        </div>

        <div className="setting-row">
          <label htmlFor="autocorrect-toggle">Auto-corrections</label>
          <input
            id="autocorrect-toggle"
            type="checkbox"
            checked={autoCorrect}
            onChange={(e) => setAutoCorrect(e.target.checked)}
          />
        </div>
      </section>
    </div>
  );
}
