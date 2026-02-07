import React, { useState, useRef, useEffect } from 'react';
import type { Editor } from '@tiptap/react';
import { useToast } from '../../hooks/useToast';
import { ShareDialog } from './ShareDialog';
import {
  exportDOCX,
  exportPDF,
  exportHTML,
  exportPlainText,
  extractTitle,
  type ExportOptions,
} from '../../services/exportService';

interface ExportMenuProps {
  editor: Editor | null;
}

export const ExportMenu: React.FC<ExportMenuProps> = ({ editor }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const { showToast } = useToast();

  const fileTypeIcons: Record<string, React.ReactNode> = {
    docx: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="#2B579A" aria-hidden="true">
        <path d="M23.004 1.5q.41 0 .703.293t.293.703v19.008q0 .41-.293.703t-.703.293H6.996q-.41 0-.703-.293T6 21.504V18H.996q-.41 0-.703-.293T0 17.004V6.996q0-.41.293-.703T.996 6H6V2.496q0-.41.293-.703t.703-.293zM6.035 11.203l1.442 4.735h1.64l1.57-7.876H9.036l-.937 4.653-1.325-4.5H5.38l-1.406 4.523-.938-4.675H1.312l1.57 7.874h1.641zM22.5 21v-3h-15v3zm0-4.5v-3.75H12v3.75zm0-5.25V7.5H12v3.75zm0-5.25V3h-15v3Z" />
      </svg>
    ),
    pdf: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="#EC1C24" aria-hidden="true">
        <path d="M23.63 15.3c-.71-.745-2.166-1.17-4.224-1.17-1.1 0-2.377.106-3.761.354a19.443 19.443 0 0 1-2.307-2.661c-.532-.71-.994-1.49-1.42-2.236.817-2.484 1.207-4.507 1.207-5.962 0-1.632-.603-3.336-2.342-3.336-.532 0-1.065.32-1.349.781-.78 1.384-.425 4.4.923 7.381a60.277 60.277 0 0 1-1.703 4.507c-.568 1.349-1.207 2.733-1.917 4.01C2.834 18.53.314 20.34.03 21.758c-.106.533.071 1.03.462 1.42.142.107.639.533 1.49.533 2.59 0 5.323-4.188 6.707-6.707 1.065-.355 2.13-.71 3.194-.994a34.963 34.963 0 0 1 3.407-.745c2.732 2.448 5.145 2.839 6.352 2.839 1.49 0 2.023-.604 2.2-1.1.32-.64.106-1.349-.213-1.704zm-1.42 1.03c-.107.532-.64.887-1.384.887-.213 0-.39-.036-.604-.071-1.348-.32-2.626-.994-3.903-2.059a17.717 17.717 0 0 1 2.98-.248c.746 0 1.385.035 1.81.142.497.106 1.278.426 1.1 1.348zm-7.524-1.668a38.01 38.01 0 0 0-2.945.674 39.68 39.68 0 0 0-2.52.745 40.05 40.05 0 0 0 1.207-2.555c.426-.994.78-2.023 1.136-2.981.354.603.745 1.207 1.135 1.739a50.127 50.127 0 0 0 1.987 2.378zM10.038 1.46a.768.768 0 0 1 .674-.425c.745 0 .887.851.887 1.526 0 1.135-.355 2.874-.958 4.861-1.03-2.768-1.1-5.074-.603-5.962zM6.134 17.997c-1.81 2.981-3.549 4.826-4.613 4.826a.872.872 0 0 1-.532-.177c-.213-.213-.32-.461-.249-.745.213-1.065 2.271-2.555 5.394-3.904Z" />
      </svg>
    ),
    html: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="#E34F26" aria-hidden="true">
        <path d="M1.5 0h21l-1.91 21.563L11.977 24l-8.564-2.438L1.5 0zm7.031 9.75l-.232-2.718 10.059.003.23-2.622L5.412 4.41l.698 8.01h9.126l-.326 3.426-2.91.804-2.955-.81-.188-2.11H6.248l.33 4.171L12 19.351l5.379-1.443.744-8.157H8.531z" />
      </svg>
    ),
    txt: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M14.727 6.727H14V0H4.91c-.905 0-1.637.732-1.637 1.636v20.728c0 .904.732 1.636 1.636 1.636h14.182c.904 0 1.636-.732 1.636-1.636V6.727h-6zm-.545 10.455H7.09v-1.364h7.09v1.364zm2.727-3.273H7.091v-1.364h9.818v1.364zm0-3.273H7.091V9.273h9.818v1.363zM14.727 6h6l-6-6v6z" />
      </svg>
    ),
    share: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="18" cy="5" r="3" />
        <circle cx="6" cy="12" r="3" />
        <circle cx="18" cy="19" r="3" />
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
      </svg>
    ),
  };

  const menuItems = [
    { label: 'Word (.docx)', action: 'docx' },
    { label: 'PDF', action: 'pdf' },
    { label: 'HTML', action: 'html' },
    { label: 'Plain Text (.txt)', action: 'txt' },
    { label: 'separator', action: 'separator' },
    { label: 'Share...', action: 'share' },
  ];

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return;

    const actionableItems = menuItems.filter((item) => item.action !== 'separator');

    switch (e.key) {
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        buttonRef.current?.focus();
        break;
      case 'ArrowDown':
        e.preventDefault();
        setFocusedIndex((prev) => {
          let next = prev + 1;
          // Skip separator
          if (menuItems[next]?.action === 'separator') next++;
          return next >= menuItems.length ? 0 : next;
        });
        break;
      case 'ArrowUp':
        e.preventDefault();
        setFocusedIndex((prev) => {
          let next = prev - 1;
          // Skip separator
          if (menuItems[next]?.action === 'separator') next--;
          return next < 0 ? actionableItems.length - 1 : next;
        });
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        const item = menuItems[focusedIndex];
        if (item && item.action !== 'separator') {
          handleMenuAction(item.action);
        }
        break;
    }
  };

  const handleExport = async (format: string) => {
    if (!editor || isExporting) return;

    setIsExporting(true);
    showToast({ type: 'info', message: `Exporting as ${format.toUpperCase()}...` });

    const html = editor.getHTML();
    const text = editor.getText();
    const title = extractTitle(html);

    const options: ExportOptions = {
      title,
      includeMetadata: true,
    };

    let result;
    switch (format) {
      case 'docx':
        result = await exportDOCX(html, options);
        break;
      case 'pdf':
        result = await exportPDF(html, options);
        break;
      case 'html':
        result = await exportHTML(html, options);
        break;
      case 'txt':
        result = await exportPlainText(text, options);
        break;
      default:
        result = { success: false, error: 'Unknown format' };
    }

    setIsExporting(false);

    if (result.success) {
      showToast({ type: 'success', message: `Document exported as ${format.toUpperCase()}` });
    } else {
      showToast({ type: 'error', message: result.error || 'Export failed' });
    }

    setIsOpen(false);
  };

  const handleMenuAction = (action: string) => {
    if (action === 'share') {
      setShareDialogOpen(true);
      setIsOpen(false);
    } else if (action !== 'separator') {
      handleExport(action);
    }
  };

  const toggleMenu = () => {
    setIsOpen(!isOpen);
    setFocusedIndex(0);
  };

  return (
    <>
      <div className="export-menu" onKeyDown={handleKeyDown}>
        <button
          ref={buttonRef}
          type="button"
          className="export-menu__button"
          onClick={toggleMenu}
          aria-label="Export options"
          aria-expanded={isOpen}
          aria-haspopup="true"
          disabled={!editor || isExporting}
        >
          Export
        </button>

        {isOpen && (
          <div ref={menuRef} className="export-menu__dropdown" role="menu">
            {menuItems.map((item, index) => {
              if (item.action === 'separator') {
                return <div key={index} className="export-menu__separator" role="separator" />;
              }

              return (
                <button
                  key={item.action}
                  type="button"
                  className={`export-menu__item ${focusedIndex === index ? 'export-menu__item--focused' : ''}`}
                  onClick={() => handleMenuAction(item.action)}
                  onMouseEnter={() => setFocusedIndex(index)}
                  role="menuitem"
                  tabIndex={focusedIndex === index ? 0 : -1}
                >
                  <span className="export-menu__item-icon">{fileTypeIcons[item.action]}</span>
                  <span className="export-menu__item-label">{item.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      <ShareDialog isOpen={shareDialogOpen} onClose={() => setShareDialogOpen(false)} />
    </>
  );
};
