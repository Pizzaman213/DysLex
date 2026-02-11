import { useState, useEffect } from 'react';
import { Editor } from '@tiptap/react';
import { CorrectionsPanel } from './CorrectionsPanel';
import { CoachPanel } from './CoachPanel';
import { FormatPanel } from './FormatPanel';
import { useEditorStore } from '../../stores/editorStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useFormatStore } from '../../stores/formatStore';
import { useCoachStore } from '../../stores/coachStore';

interface RightPanelProps {
  editor: Editor | null;
}

type Tab = 'suggestions' | 'coach' | 'format';

export function RightPanel({ editor }: RightPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('suggestions');
  const corrections = useEditorStore((s) => s.corrections);
  const aiCoaching = useSettingsStore((s) => s.aiCoaching);
  const activeFormat = useFormatStore((s) => s.activeFormat);
  const formatIssues = useFormatStore((s) => s.issues);

  const pendingExplain = useCoachStore((s) => s.pendingExplainCorrection);

  // Auto-switch to Coach tab when a correction explanation is requested
  useEffect(() => {
    if (pendingExplain) {
      setActiveTab('coach');
    }
  }, [pendingExplain]);

  const activeCount = corrections.filter((c) => !c.isApplied && !c.isDismissed).length;
  const formatIssueCount = formatIssues.filter((i) => i.severity !== 'info').length;
  const showFormatTab = activeFormat !== 'none';

  return (
    <div className="right-panel">
      <div className="right-panel__tabs" role="tablist">
        <button
          className={`right-panel__tab${activeTab === 'suggestions' ? ' right-panel__tab--active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'suggestions'}
          type="button"
          onClick={() => setActiveTab('suggestions')}
        >
          Suggestions
          {activeCount > 0 && (
            <span className="right-panel__badge">{activeCount}</span>
          )}
        </button>

        {aiCoaching && (
          <button
            className={`right-panel__tab${activeTab === 'coach' ? ' right-panel__tab--active' : ''}`}
            role="tab"
            aria-selected={activeTab === 'coach'}
            type="button"
            onClick={() => setActiveTab('coach')}
          >
            Coach
          </button>
        )}

        {showFormatTab && (
          <button
            className={`right-panel__tab${activeTab === 'format' ? ' right-panel__tab--active' : ''}`}
            role="tab"
            aria-selected={activeTab === 'format'}
            type="button"
            onClick={() => setActiveTab('format')}
          >
            Format
            {formatIssueCount > 0 && (
              <span className="right-panel__badge">{formatIssueCount}</span>
            )}
          </button>
        )}
      </div>

      <div className="right-panel__content">
        {activeTab === 'suggestions' && <CorrectionsPanel editor={editor} />}
        {activeTab === 'coach' && aiCoaching && <CoachPanel editor={editor} />}
        {activeTab === 'format' && <FormatPanel editor={editor} />}
      </div>
    </div>
  );
}
