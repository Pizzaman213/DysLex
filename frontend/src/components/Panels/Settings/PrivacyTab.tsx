import { useState } from 'react';
import { api } from '@/services/api';

// Stripped out data-sharing toggles — those belong in a consent modal, not settings.
// Kept just the GDPR export/delete actions. — C. Secrist, 2/9
export function PrivacyTab() {
  const [isExporting, setIsExporting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteInput, setDeleteInput] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const handleExportData = async () => {
    setIsExporting(true);
    try {
      const userId = '00000000-0000-0000-0000-000000000000';
      const blob = await api.exportUserData(userId);

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dyslex-data-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setToast({ message: 'Data exported successfully', type: 'success' });
      setTimeout(() => setToast(null), 3000);
    } catch (error) {
      console.error('Export failed:', error);
      setToast({ message: 'Export failed. Please try again.', type: 'error' });
      setTimeout(() => setToast(null), 3000);
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteData = async () => {
    if (deleteInput !== 'DELETE') {
      setToast({ message: 'Please type DELETE to confirm', type: 'error' });
      setTimeout(() => setToast(null), 3000);
      return;
    }

    setIsDeleting(true);
    try {
      const userId = '00000000-0000-0000-0000-000000000000';
      await api.deleteUserData(userId);

      localStorage.clear();

      setToast({ message: 'All data deleted. Redirecting...', type: 'success' });

      setTimeout(() => {
        window.location.href = '/';
      }, 2000);
    } catch (error) {
      console.error('Delete failed:', error);
      setToast({ message: 'Delete failed. Please try again.', type: 'error' });
      setTimeout(() => setToast(null), 3000);
      setIsDeleting(false);
    }
  };

  return (
    <div className="settings-tab-content" role="tabpanel" id="privacy-panel" aria-labelledby="privacy-tab">
      <h2>Privacy & Data</h2>

      <div className="setting-section">
        <div className="setting-section-header">
          <h3>Data Management</h3>
          <p className="setting-section-desc">Export or delete your personal data</p>
        </div>

        <div className="privacy-action-card">
          <div className="action-card-content">
            <h4>Download My Data</h4>
            <p>Export all your data as JSON (GDPR data portability)</p>
          </div>
          <button
            className="action-button primary"
            onClick={handleExportData}
            disabled={isExporting}
          >
            {isExporting ? 'Exporting...' : 'Download'}
          </button>
        </div>

        <div className="privacy-action-card">
          <div className="action-card-content">
            <h4>Delete All Data</h4>
            <p>Permanently delete your account and all associated data</p>
          </div>
          <button
            className="action-button destructive"
            onClick={() => setShowDeleteConfirm(true)}
          >
            Delete
          </button>
        </div>
      </div>

      {showDeleteConfirm && (
        <div className="delete-confirm-dialog" role="dialog" aria-labelledby="delete-dialog-title">
          <div className="dialog-overlay" onClick={() => setShowDeleteConfirm(false)}></div>
          <div className="dialog-content">
            <h3 id="delete-dialog-title">Confirm Deletion</h3>
            <p>
              This will permanently delete your account, settings, error profile, and all learning
              data. This action <strong>cannot be undone</strong>.
            </p>
            <p>Type <strong>DELETE</strong> to confirm:</p>
            <input
              type="text"
              value={deleteInput}
              onChange={(e) => setDeleteInput(e.target.value)}
              placeholder="Type DELETE"
              className="delete-confirm-input"
              autoFocus
            />
            <div className="dialog-actions">
              <button
                className="action-button"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteInput('');
                }}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                className="action-button destructive"
                onClick={handleDeleteData}
                disabled={deleteInput !== 'DELETE' || isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete Everything'}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className={`toast ${toast.type}`} role="alert">
          {toast.message}
        </div>
      )}
    </div>
  );
}
