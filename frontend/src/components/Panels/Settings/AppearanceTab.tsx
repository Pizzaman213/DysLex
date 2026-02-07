import { useSettingsStore } from '@/stores/settingsStore';
import { ThemeSwitcher } from '@/components/Shared/ThemeSwitcher';
import { FontSelector } from '@/components/Shared/FontSelector';
import { PageTypeSelector } from '@/components/Shared/PageTypeSelector';
import type { ViewMode } from '@/types';

export function AppearanceTab() {
  const {
    viewMode,
    showZoom,
    fontSize,
    lineSpacing,
    letterSpacing,
    setViewMode,
    setShowZoom,
    setFontSize,
    setLineSpacing,
    setLetterSpacing,
  } = useSettingsStore();

  return (
    <div className="settings-tab-content" role="tabpanel" id="appearance-panel" aria-labelledby="appearance-tab">
      <h2>Appearance</h2>

      <div className="setting-section">
        <div className="setting-section-header">
          <h3>Theme & Layout</h3>
          <p className="setting-section-desc">Customize the look and feel of your workspace</p>
        </div>

        <div className="setting-row">
          <label htmlFor="theme-switcher">
            <span className="setting-label">Color Theme</span>
            <span className="setting-help">Choose your preferred color scheme</span>
          </label>
          <div id="theme-switcher">
            <ThemeSwitcher />
          </div>
        </div>

        <div className="setting-row">
          <label htmlFor="font-selector">
            <span className="setting-label">Font</span>
            <span className="setting-help">Dyslexia-friendly fonts for comfortable reading</span>
          </label>
          <div id="font-selector">
            <FontSelector />
          </div>
        </div>

        <div className="setting-row">
          <label htmlFor="view-mode-selector">
            <span className="setting-label">View Mode</span>
            <span className="setting-help">Paper view shows page breaks; continuous flow is a single scroll</span>
          </label>
          <select
            id="view-mode-selector"
            className="setting-select"
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as ViewMode)}
          >
            <option value="paper">Paper View</option>
            <option value="continuous">Continuous Flow</option>
          </select>
        </div>

        {viewMode === 'paper' && (
          <div className="setting-row">
            <label htmlFor="page-type-selector">
              <span className="setting-label">Page Type</span>
              <span className="setting-help">Set editor page width</span>
            </label>
            <div id="page-type-selector">
              <PageTypeSelector />
            </div>
          </div>
        )}

        <div className="setting-row">
          <label htmlFor="show-zoom-toggle">
            <span className="setting-label">Zoom Controls</span>
            <span className="setting-help">Show zoom buttons in the editor toolbar</span>
          </label>
          <input
            type="checkbox"
            id="show-zoom-toggle"
            className="setting-toggle"
            checked={showZoom}
            onChange={(e) => setShowZoom(e.target.checked)}
          />
        </div>

      </div>

      <div className="setting-section">
        <div className="setting-section-header">
          <h3>Typography</h3>
          <p className="setting-section-desc">Fine-tune text size and spacing for readability</p>
        </div>

        <div className="setting-row">
          <label htmlFor="font-size-slider">
            <span className="setting-label">Font Size</span>
            <span className="setting-help">{fontSize}px</span>
          </label>
          <input
            type="range"
            id="font-size-slider"
            min="8"
            max="72"
            step="1"
            value={fontSize}
            onChange={(e) => setFontSize(Number(e.target.value))}
            className="setting-slider"
            aria-valuenow={fontSize}
            aria-valuemin={8}
            aria-valuemax={72}
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
