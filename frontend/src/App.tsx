import { useState } from 'react';
import { Editor } from './components/Editor/Editor';
import { Toolbar } from './components/Editor/Toolbar';
import { CorrectionsPanel } from './components/Panels/CorrectionsPanel';
import { ProgressDashboard } from './components/Panels/ProgressDashboard';
import { SettingsPanel } from './components/Panels/SettingsPanel';
import { StatusBar } from './components/Shared/StatusBar';
import { ThemeSwitcher } from './components/Shared/ThemeSwitcher';
import { useSettingsStore } from './stores/settingsStore';

type WritingMode = 'capture' | 'mindmap' | 'draft' | 'polish';
type Panel = 'corrections' | 'progress' | 'settings' | null;

export function App() {
  const [mode, setMode] = useState<WritingMode>('draft');
  const [activePanel, setActivePanel] = useState<Panel>(null);
  const { theme } = useSettingsStore();

  return (
    <div className={`app theme-${theme}`}>
      <header className="app-header">
        <h1 className="app-title">DysLex AI</h1>
        <nav className="mode-nav">
          <button
            className={`mode-btn ${mode === 'capture' ? 'active' : ''}`}
            onClick={() => setMode('capture')}
            aria-pressed={mode === 'capture'}
          >
            Capture
          </button>
          <button
            className={`mode-btn ${mode === 'mindmap' ? 'active' : ''}`}
            onClick={() => setMode('mindmap')}
            aria-pressed={mode === 'mindmap'}
          >
            Mind Map
          </button>
          <button
            className={`mode-btn ${mode === 'draft' ? 'active' : ''}`}
            onClick={() => setMode('draft')}
            aria-pressed={mode === 'draft'}
          >
            Draft
          </button>
          <button
            className={`mode-btn ${mode === 'polish' ? 'active' : ''}`}
            onClick={() => setMode('polish')}
            aria-pressed={mode === 'polish'}
          >
            Polish
          </button>
        </nav>
        <div className="header-actions">
          <ThemeSwitcher />
          <button
            className="panel-btn"
            onClick={() => setActivePanel(activePanel === 'settings' ? null : 'settings')}
            aria-label="Settings"
          >
            Settings
          </button>
        </div>
      </header>

      <main className="app-main">
        <div className="editor-container">
          <Toolbar mode={mode} />
          <Editor mode={mode} />
        </div>

        {activePanel && (
          <aside className="panel-container">
            {activePanel === 'corrections' && <CorrectionsPanel />}
            {activePanel === 'progress' && <ProgressDashboard />}
            {activePanel === 'settings' && <SettingsPanel />}
          </aside>
        )}
      </main>

      <StatusBar
        onPanelToggle={(panel) => setActivePanel(activePanel === panel ? null : panel)}
      />
    </div>
  );
}
