import { useState } from 'react';
import { useDocumentStore } from '@/stores/documentStore';
import { useEditorStore } from '@/stores/editorStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useMediaQuery, MOBILE_QUERY } from '@/hooks/useMediaQuery';
import { ExportMenu } from '@/components/Editor/ExportMenu';
import { UserMenu } from '@/components/Layout/UserMenu';

export function Topbar() {
  const { documents, activeDocumentId, updateDocumentTitle } = useDocumentStore();
  const { editorInstance } = useEditorStore();
  const { mobileSidebarOpen, setMobileSidebarOpen } = useSettingsStore();
  const isMobile = useMediaQuery(MOBILE_QUERY);
  const activeDoc = documents.find((d) => d.id === activeDocumentId);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');

  const handleStartEdit = () => {
    if (activeDoc) {
      setEditTitle(activeDoc.title);
      setIsEditing(true);
    }
  };

  const handleSaveTitle = () => {
    if (activeDoc && editTitle.trim()) {
      updateDocumentTitle(activeDoc.id, editTitle.trim());
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSaveTitle();
    if (e.key === 'Escape') setIsEditing(false);
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        {isMobile && (
          <button
            className="topbar-hamburger"
            onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
            aria-label={mobileSidebarOpen ? 'Close menu' : 'Open menu'}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        )}
      </div>

      <div className="topbar-center">
        {isEditing ? (
          <input
            className="topbar-title-input"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onBlur={handleSaveTitle}
            onKeyDown={handleKeyDown}
            autoFocus
          />
        ) : (
          <button
            className="topbar-title"
            onClick={handleStartEdit}
            title="Click to rename"
          >
            {activeDoc?.title || 'Untitled Document'}
          </button>
        )}
      </div>

      <div className="topbar-right">
        <ExportMenu editor={editorInstance} />
        <UserMenu />
      </div>
    </header>
  );
}
