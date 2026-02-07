import React, { useState } from 'react';
import { Dialog } from '../Shared/Dialog';
import { useToast } from '../../hooks/useToast';

interface ShareDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ShareDialog: React.FC<ShareDialogProps> = ({ isOpen, onClose }) => {
  const { showToast } = useToast();
  const [shareableLink] = useState(
    () => `https://dyslex.ai/doc/${crypto.randomUUID().split('-')[0]}`
  );

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareableLink);
      showToast({ type: 'success', message: 'Link copied to clipboard!' });
    } catch (error) {
      // Fallback for older browsers
      try {
        const textarea = document.createElement('textarea');
        textarea.value = shareableLink;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast({ type: 'success', message: 'Link copied to clipboard!' });
      } catch (fallbackError) {
        showToast({ type: 'error', message: 'Failed to copy link' });
      }
    }
  };

  const handleEmailShare = () => {
    showToast({ type: 'info', message: 'Email sharing coming soon!' });
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Share Document" size="md">
      <div className="share-dialog">
        {/* Copy Link Section */}
        <div className="share-dialog__section">
          <div className="share-dialog__icon">📋</div>
          <h3 className="share-dialog__section-title">Copy Shareable Link</h3>
          <div className="share-dialog__link-display">{shareableLink}</div>
          <button
            type="button"
            className="share-dialog__button share-dialog__button--primary"
            onClick={handleCopyLink}
          >
            Copy Link
          </button>
        </div>

        {/* Email Share Section */}
        <div className="share-dialog__section">
          <div className="share-dialog__icon">✉️</div>
          <h3 className="share-dialog__section-title">Share via Email</h3>
          <button
            type="button"
            className="share-dialog__button share-dialog__button--secondary"
            onClick={handleEmailShare}
          >
            Share via Email
          </button>
        </div>

        {/* Collaboration Info */}
        <div className="share-dialog__info">
          <div className="share-dialog__icon">ℹ️</div>
          <div className="share-dialog__info-content">
            <h4 className="share-dialog__info-title">Collaboration Features</h4>
            <p className="share-dialog__info-text">
              Real-time collaboration coming soon! For now, export and share documents via
              your preferred cloud storage or email.
            </p>
          </div>
        </div>
      </div>
    </Dialog>
  );
};
