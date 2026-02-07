import { useState } from 'react';
import { useDocumentStore } from '@/stores/documentStore';
import { useEditorStore } from '@/stores/editorStore';
import { ExportMenu } from '@/components/Editor/ExportMenu';

export function Topbar() {
  const { documents, activeDocumentId, updateDocumentTitle } = useDocumentStore();
  const { editorInstance } = useEditorStore();
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
        <svg className="topbar-logo" width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <rect width="28" height="28" rx="8" fill="var(--accent)" />
          <path d="M8 8h4v12H8V8zm6 0h4c2.2 0 4 1.8 4 4s-1.8 4-4 4h-4V8z" fill="var(--text-inverse, #fff)" />
        </svg>
        <span className="topbar-brand">DysLex AI</span>
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
        <div className="topbar-avatar" aria-label="User avatar">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <circle cx="8" cy="5" r="3" />
            <path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6" />
          </svg>
        </div>
      </div>
    </header>
  );
}
