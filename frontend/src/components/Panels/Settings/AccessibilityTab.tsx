import { useSettingsStore } from '@/stores/settingsStore';

export function AccessibilityTab() {
  const {
    voiceEnabled,
    autoCorrect,
    focusMode,
    ttsSpeed,
    correctionAggressiveness,
    developerMode,
    setVoiceEnabled,
    setAutoCorrect,
    setFocusMode,
    setTtsSpeed,
    setCorrectionAggressiveness,
    setDeveloperMode,
  } = useSettingsStore();

  const aggressivenessLabels = ['Off', 'Light', 'Standard', 'Aggressive'];
  const aggressivenessLevel = Math.floor(correctionAggressiveness / 33.34);

  return (
    <div className="settings-tab-content" role="tabpanel" id="accessibility-panel" aria-labelledby="accessibility-tab">
      <h2>Accessibility</h2>

      <div className="setting-row">
        <label htmlFor="voice-enabled-toggle">
          <span className="setting-label">Voice Input</span>
          <span className="setting-help">Enable microphone for voice-to-text</span>
        </label>
        <button
          id="voice-enabled-toggle"
          role="switch"
          aria-checked={voiceEnabled}
          className={`setting-toggle ${voiceEnabled ? 'active' : ''}`}
          onClick={() => setVoiceEnabled(!voiceEnabled)}
        >
          <span className="toggle-slider"></span>
        </button>
      </div>

      <div className="setting-row">
        <label htmlFor="auto-correct-toggle">
          <span className="setting-label">Auto-Correct</span>
          <span className="setting-help">Automatically apply corrections while typing</span>
        </label>
        <button
          id="auto-correct-toggle"
          role="switch"
          aria-checked={autoCorrect}
          className={`setting-toggle ${autoCorrect ? 'active' : ''}`}
          onClick={() => setAutoCorrect(!autoCorrect)}
        >
          <span className="toggle-slider"></span>
        </button>
      </div>

      <div className="setting-row">
        <label htmlFor="focus-mode-toggle">
          <span className="setting-label">Focus Mode Default</span>
          <span className="setting-help">Start writing sessions in focus mode</span>
        </label>
        <button
          id="focus-mode-toggle"
          role="switch"
          aria-checked={focusMode}
          className={`setting-toggle ${focusMode ? 'active' : ''}`}
          onClick={() => setFocusMode(!focusMode)}
        >
          <span className="toggle-slider"></span>
        </button>
      </div>

      <div className="setting-row">
        <label htmlFor="tts-speed-slider">
          <span className="setting-label">Text-to-Speech Speed</span>
          <span className="setting-help">{ttsSpeed.toFixed(1)}x</span>
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
          aria-describedby="tts-speed-help"
        />
      </div>

      <div className="setting-row">
        <label htmlFor="correction-aggressiveness-slider">
          <span className="setting-label">Correction Aggressiveness</span>
          <span className="setting-help">{aggressivenessLabels[aggressivenessLevel]}</span>
        </label>
        <input
          type="range"
          id="correction-aggressiveness-slider"
          min="0"
          max="100"
          step="25"
          value={correctionAggressiveness}
          onChange={(e) => setCorrectionAggressiveness(Number(e.target.value))}
          className="setting-slider with-labels"
          aria-valuenow={correctionAggressiveness}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-describedby="correction-aggressiveness-help"
          list="aggressiveness-markers"
        />
        <datalist id="aggressiveness-markers">
          <option value="0" label="Off"></option>
          <option value="33" label="Light"></option>
          <option value="66" label="Standard"></option>
          <option value="100" label="Aggressive"></option>
        </datalist>
      </div>

      <div className="setting-section-divider"></div>

      <h3>Advanced</h3>

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
  );
}
