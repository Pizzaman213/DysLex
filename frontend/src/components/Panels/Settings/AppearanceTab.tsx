import { useSettingsStore } from '@/stores/settingsStore';
import { ThemeSwitcher } from '@/components/Shared/ThemeSwitcher';
import { FontSelector } from '@/components/Shared/FontSelector';

export function AppearanceTab() {
  const {
    fontSize,
    lineSpacing,
    letterSpacing,
    setFontSize,
    setLineSpacing,
    setLetterSpacing,
  } = useSettingsStore();

  return (
    <div className="settings-tab-content" role="tabpanel" id="appearance-panel" aria-labelledby="appearance-tab">
      <h2>Appearance</h2>

      <div className="setting-row">
        <label htmlFor="theme-switcher">
          <span className="setting-label">Theme</span>
          <span className="setting-help">Choose your preferred color scheme</span>
        </label>
        <div id="theme-switcher">
          <ThemeSwitcher />
        </div>
      </div>

      <div className="setting-row">
        <label htmlFor="font-selector">
          <span className="setting-label">Font</span>
          <span className="setting-help">Dyslexia-friendly fonts</span>
        </label>
        <div id="font-selector">
          <FontSelector />
        </div>
      </div>

      <div className="setting-row">
        <label htmlFor="font-size-slider">
          <span className="setting-label">Font Size</span>
          <span className="setting-help">{fontSize}px</span>
        </label>
        <input
          type="range"
          id="font-size-slider"
          min="16"
          max="24"
          step="1"
          value={fontSize}
          onChange={(e) => setFontSize(Number(e.target.value))}
          className="setting-slider"
          aria-valuenow={fontSize}
          aria-valuemin={16}
          aria-valuemax={24}
        />
      </div>

      <div className="setting-row">
        <label htmlFor="line-spacing-slider">
          <span className="setting-label">Line Spacing</span>
          <span className="setting-help">{lineSpacing.toFixed(2)}x</span>
        </label>
        <input
          type="range"
          id="line-spacing-slider"
          min="1.5"
          max="2.0"
          step="0.05"
          value={lineSpacing}
          onChange={(e) => setLineSpacing(Number(e.target.value))}
          className="setting-slider"
          aria-valuenow={lineSpacing}
          aria-valuemin={1.5}
          aria-valuemax={2.0}
        />
      </div>

      <div className="setting-row">
        <label htmlFor="letter-spacing-slider">
          <span className="setting-label">Letter Spacing</span>
          <span className="setting-help">{letterSpacing.toFixed(2)}em</span>
        </label>
        <input
          type="range"
          id="letter-spacing-slider"
          min="0.05"
          max="0.12"
          step="0.01"
          value={letterSpacing}
          onChange={(e) => setLetterSpacing(Number(e.target.value))}
          className="setting-slider"
          aria-valuenow={letterSpacing}
          aria-valuemin={0.05}
          aria-valuemax={0.12}
        />
      </div>

      <div className="setting-preview">
        <h3>Preview</h3>
        <p style={{
          fontSize: `${fontSize}px`,
          lineHeight: lineSpacing,
          letterSpacing: `${letterSpacing}em`,
        }}>
          The quick brown fox jumps over the lazy dog. This sentence shows how your text will appear with the current settings.
        </p>
      </div>
    </div>
  );
}
