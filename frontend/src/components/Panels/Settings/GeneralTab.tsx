import { useSettingsStore } from '@/stores/settingsStore';
import type { Language } from '@/types';

export function GeneralTab() {
  const {
    language,
    setLanguage,
    mindMapEnabled,
    setMindMapEnabled,
    draftModeEnabled,
    setDraftModeEnabled,
    polishModeEnabled,
    setPolishModeEnabled,
    voiceEnabled,
    setVoiceEnabled,
    passiveLearning,
    setPassiveLearning,
    aiCoaching,
    setAiCoaching,
    inlineCorrections,
    setInlineCorrections,
    progressTracking,
    setProgressTracking,
    readAloud,
    setReadAloud,
    autoCorrect,
    setAutoCorrect,
    focusMode,
    setFocusMode,
  } = useSettingsStore();

  const languages: { value: Language; label: string }[] = [
    { value: 'en', label: 'English' },
    { value: 'es', label: 'Espanol' },
    { value: 'fr', label: 'Francais' },
    { value: 'de', label: 'Deutsch' },
  ];

  return (
    <div className="settings-tab-content" role="tabpanel" id="general-panel" aria-labelledby="general-tab">
      <h2>General Settings</h2>

      {/* Language */}
      <div className="setting-section">
        <div className="setting-section-header">
          <h3>Language</h3>
          <p className="setting-section-desc">Interface and correction language</p>
        </div>
        <div className="setting-row">
          <label htmlFor="language-select">
            <span className="setting-label">Display Language</span>
            <span className="setting-help">Changes text throughout the app</span>
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
      </div>

      {/* Writing Modes */}
      <div className="setting-section">
        <div className="setting-section-header">
          <h3>Writing Modes</h3>
          <p className="setting-section-desc">Choose which writing modes appear in the sidebar</p>
        </div>

        <div className="setting-row">
          <label htmlFor="mindmap-toggle">
            <span className="setting-label">Mind Map</span>
            <span className="setting-help">Visual idea organization with drag-and-drop cards</span>
          </label>
          <button
            id="mindmap-toggle"
            role="switch"
            aria-checked={mindMapEnabled}
            className={`setting-toggle ${mindMapEnabled ? 'active' : ''}`}
            onClick={() => setMindMapEnabled(!mindMapEnabled)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>

        <div className="setting-row">
          <label htmlFor="draft-toggle">
            <span className="setting-label">Draft Mode</span>
            <span className="setting-help">Scaffolded writing with AI coaching and corrections</span>
          </label>
          <button
            id="draft-toggle"
            role="switch"
            aria-checked={draftModeEnabled}
            className={`setting-toggle ${draftModeEnabled ? 'active' : ''}`}
            onClick={() => setDraftModeEnabled(!draftModeEnabled)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>

        <div className="setting-row">
          <label htmlFor="polish-toggle">
            <span className="setting-label">Polish Mode</span>
            <span className="setting-help">Review and refine with tracked changes and readability scoring</span>
          </label>
          <button
            id="polish-toggle"
            role="switch"
            aria-checked={polishModeEnabled}
            className={`setting-toggle ${polishModeEnabled ? 'active' : ''}`}
            onClick={() => setPolishModeEnabled(!polishModeEnabled)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>
      </div>

      {/* AI Features */}
      <div className="setting-section">
        <div className="setting-section-header">
          <h3>AI Features</h3>
          <p className="setting-section-desc">Control how the AI assists your writing</p>
        </div>

        <div className="setting-row">
          <label htmlFor="autocorrect-toggle">
            <span className="setting-label">Auto-Correct</span>
            <span className="setting-help">Automatically apply corrections while typing</span>
          </label>
          <button
            id="autocorrect-toggle"
            role="switch"
            aria-checked={autoCorrect}
            className={`setting-toggle ${autoCorrect ? 'active' : ''}`}
            onClick={() => setAutoCorrect(!autoCorrect)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>

        <div className="setting-row">
          <label htmlFor="inline-corrections-toggle">
            <span className="setting-label">Inline Corrections</span>
            <span className="setting-help">Show subtle underlines for spelling and grammar suggestions</span>
          </label>
          <button
            id="inline-corrections-toggle"
            role="switch"
            aria-checked={inlineCorrections}
            className={`setting-toggle ${inlineCorrections ? 'active' : ''}`}
            onClick={() => setInlineCorrections(!inlineCorrections)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>

        <div className="setting-row">
          <label htmlFor="passive-learning-toggle">
            <span className="setting-label">Passive Learning</span>
            <span className="setting-help">Silently learn your writing patterns to improve suggestions over time</span>
          </label>
          <button
            id="passive-learning-toggle"
            role="switch"
            aria-checked={passiveLearning}
            className={`setting-toggle ${passiveLearning ? 'active' : ''}`}
            onClick={() => setPassiveLearning(!passiveLearning)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>

        <div className="setting-row">
          <label htmlFor="ai-coaching-toggle">
            <span className="setting-label">AI Writing Coach</span>
            <span className="setting-help">Get gentle nudges and suggestions while writing in Draft mode</span>
          </label>
          <button
            id="ai-coaching-toggle"
            role="switch"
            aria-checked={aiCoaching}
            className={`setting-toggle ${aiCoaching ? 'active' : ''}`}
            onClick={() => setAiCoaching(!aiCoaching)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>
      </div>

      {/* Tools */}
      <div className="setting-section">
        <div className="setting-section-header">
          <h3>Tools</h3>
          <p className="setting-section-desc">Enable or disable built-in tools</p>
        </div>

        <div className="setting-row">
          <label htmlFor="voice-toggle">
            <span className="setting-label">Voice Input</span>
            <span className="setting-help">Use your microphone for voice-to-text in Capture mode</span>
          </label>
          <button
            id="voice-toggle"
            role="switch"
            aria-checked={voiceEnabled}
            className={`setting-toggle ${voiceEnabled ? 'active' : ''}`}
            onClick={() => setVoiceEnabled(!voiceEnabled)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>

        <div className="setting-row">
          <label htmlFor="read-aloud-toggle">
            <span className="setting-label">Read Aloud</span>
            <span className="setting-help">Text-to-speech to hear your writing read back to you</span>
          </label>
          <button
            id="read-aloud-toggle"
            role="switch"
            aria-checked={readAloud}
            className={`setting-toggle ${readAloud ? 'active' : ''}`}
            onClick={() => setReadAloud(!readAloud)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>

        <div className="setting-row">
          <label htmlFor="focus-mode-toggle">
            <span className="setting-label">Focus Mode</span>
            <span className="setting-help">Dim everything except the current paragraph while writing</span>
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
          <label htmlFor="progress-toggle">
            <span className="setting-label">Progress Tracking</span>
            <span className="setting-help">Track your writing improvement over time</span>
          </label>
          <button
            id="progress-toggle"
            role="switch"
            aria-checked={progressTracking}
            className={`setting-toggle ${progressTracking ? 'active' : ''}`}
            onClick={() => setProgressTracking(!progressTracking)}
          >
            <span className="toggle-slider"></span>
          </button>
        </div>
      </div>
    </div>
  );
}
