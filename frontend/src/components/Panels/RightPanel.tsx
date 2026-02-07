import { useState } from 'react';
import { Editor } from '@tiptap/react';
import { CorrectionsPanel } from './CorrectionsPanel';
import { CoachPanel } from './CoachPanel';
import { useEditorStore } from '../../stores/editorStore';
import { useSettingsStore } from '../../stores/settingsStore';

interface RightPanelProps {
  editor: Editor | null;
}

type Tab = 'suggestions' | 'coach';

export function RightPanel({ editor }: RightPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('suggestions');
  const corrections = useEditorStore((s) => s.corrections);
  const aiCoaching = useSettingsStore((s) => s.aiCoaching);

  const activeCount = corrections.filter((c) => !c.isApplied && !c.isDismissed).length;

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
      </div>

      <div className="right-panel__content">
        {activeTab === 'suggestions' && <CorrectionsPanel editor={editor} />}
        {activeTab === 'coach' && aiCoaching && <CoachPanel editor={editor} />}
      </div>
    </div>
  );
}
