import { useEditorStore } from '@/stores/editorStore';
import { useEffect, useState } from 'react';
import { parseText } from '@/utils/readabilityUtils';

export function StatusBar() {
  const { content, corrections, isSaving } = useEditorStore();
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  const { wordCount } = parseText(content);
  const suggestionCount = corrections.filter((c) => !c.isApplied && !c.isDismissed).length;

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const getCurrentMode = () => {
    const path = window.location.pathname;
    if (path.includes('capture')) return 'Capture';
    if (path.includes('mindmap')) return 'Mind Map';
    if (path.includes('draft')) return 'Draft';
    if (path.includes('polish')) return 'Polish';
    return 'Writing';
  };

  return (
    <footer className="status-bar" role="contentinfo">
      <div className="status-left">
        <span className={`sdot ${!isOnline ? 'sdot-offline' : ''}`} />
        <span className="status-item status-mode">{getCurrentMode()}</span>
        {isSaving && <span className="status-saving">Saving...</span>}
      </div>
      <div className="status-right">
        <span className="status-item">{wordCount} words</span>
        {suggestionCount > 0 && (
          <span className="status-item">{suggestionCount} suggestions</span>
        )}
        <span className="status-item">{isSaving ? 'Saving...' : 'Saved'}</span>
      </div>
    </footer>
  );
}
