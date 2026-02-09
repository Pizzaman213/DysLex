import { useSettingsStore } from '@/stores/settingsStore';

export function AccessibilityTab() {
  const {
    ttsSpeed,
    correctionAggressiveness,
    developerMode,
    setTtsSpeed,
    setCorrectionAggressiveness,
    setDeveloperMode,
  } = useSettingsStore();

  const aggressivenessLabels = ['Off', 'Light', 'Standard', 'Aggressive'];
  const aggressivenessLevel = Math.floor(correctionAggressiveness / 33.34);

  return (
    <div className="settings-tab-content" role="tabpanel" id="accessibility-panel" aria-labelledby="accessibility-tab">
      <h2>Accessibility</h2>

      {/* Reading Assistance */}
      <div className="setting-section">
        <div className="setting-section-header">
          <h3>Reading Assistance</h3>
          <p className="setting-section-desc">Fine-tune how text-to-speech and corrections behave</p>
        </div>

        <div className="setting-row">
          <label htmlFor="tts-speed-slider">
            <span className="setting-label">Text-to-Speech Speed</span>
            <span className="setting-help">{ttsSpeed.toFixed(1)}x playback speed</span>
          </label>
          <input
            type="range"
            id="tts-speed-slider"
            min="0.5"
            max="2.0"
            step="0.1"
            value={ttsSpeed}
            onChange={(e) => setTtsSpeed(Number(e.target.value))}
            className="setting-slider"
            aria-valuenow={ttsSpeed}
            aria-valuemin={0.5}
            aria-valuemax={2.0}
          />
        </div>

        <div className="setting-row">
          <label htmlFor="correction-aggressiveness-slider">
            <span className="setting-label">Correction Sensitivity</span>
            <span className="setting-help">
              {aggressivenessLabels[aggressivenessLevel]} — how aggressively corrections are applied
            </span>
          </label>
          <input
            type="range"
            id="correction-aggressiveness-slider"
            min="0"
            max="100"
            step="25"
            value={correctionAggressiveness}
            onChange={(e) => setCorrectionAggressiveness(Number(e.target.value))}
            className="setting-slider" // simplified from with-labels class — cs feb 8
            aria-valuenow={correctionAggressiveness}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      {/* Advanced */}
      <div className="setting-section">
        <div className="setting-section-header">
          <h3>Advanced</h3>
          <p className="setting-section-desc">Options for power users and developers</p>
        </div>

        <div className="setting-row">
          <label htmlFor="developer-mode-toggle">
            <span className="setting-label">Developer Mode</span>
            <span className="setting-help">Show technical documentation and debug info</span>
          </label>
          <button
            id="developer-mode-toggle"
            role="switch"
            aria-checked={developerMode}
            className={`setting-toggle ${developerMode ? 'active' : ''}`}
            onClick={() => setDeveloperMode(!developerMode)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>
      </div>
    </div>
  );
}
