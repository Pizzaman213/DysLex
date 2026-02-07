import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Topbar } from '../Topbar';
import { useDocumentStore } from '@/stores/documentStore';
import { useEditorStore } from '@/stores/editorStore';

vi.mock('@/components/Editor/ExportMenu', () => ({
  ExportMenu: () => <div data-testid="export-menu" />,
}));

vi.mock('@/components/Layout/UserMenu', () => ({
  UserMenu: () => <div data-testid="user-menu" />,
}));

vi.mock('@/services/documentSync', () => ({
  syncCreateDocument: vi.fn(),
  syncDeleteDocument: vi.fn(),
  syncUpdateDocumentTitle: vi.fn(),
  syncUpdateDocumentContent: vi.fn(),
  syncCreateFolder: vi.fn(),
  syncDeleteFolder: vi.fn(),
  syncRenameFolder: vi.fn(),
  syncMoveDocument: vi.fn(),
  initializeFromServer: vi.fn(),
}));

describe('Topbar', () => {
  beforeEach(() => {
    useDocumentStore.setState({
      documents: [
        {
          id: 'doc-1',
          title: 'My Document',
          content: '',
          mode: 'draft',
          createdAt: Date.now(),
          updatedAt: Date.now(),
          folderId: null,
        },
      ],
      activeDocumentId: 'doc-1',
      folders: [],
      rootOrder: ['doc-1'],
      folderOrders: {},
    });
    useEditorStore.setState({ editorInstance: null });
  });

  it('displays the active document title', () => {
    render(<Topbar />);
    expect(screen.getByText('My Document')).toBeInTheDocument();
  });

  it('enters edit mode when the title is clicked', () => {
    render(<Topbar />);
    fireEvent.click(screen.getByText('My Document'));
    const input = document.querySelector('.topbar-title-input') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input.value).toBe('My Document');
  });

  it('saves the new title on Enter key', () => {
    render(<Topbar />);
    fireEvent.click(screen.getByText('My Document'));
    const input = document.querySelector('.topbar-title-input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Renamed Doc' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    const doc = useDocumentStore.getState().documents.find((d) => d.id === 'doc-1');
    expect(doc?.title).toBe('Renamed Doc');
  });

  it('cancels editing on Escape key without updating the store', () => {
    render(<Topbar />);
    fireEvent.click(screen.getByText('My Document'));
    const input = document.querySelector('.topbar-title-input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Changed' } });
    fireEvent.keyDown(input, { key: 'Escape' });
    // Input should be gone (edit mode exited)
    expect(document.querySelector('.topbar-title-input')).not.toBeInTheDocument();
    // Title should remain unchanged
    const doc = useDocumentStore.getState().documents.find((d) => d.id === 'doc-1');
    expect(doc?.title).toBe('My Document');
  });

  it('does not save an empty title on blur', () => {
    render(<Topbar />);
    fireEvent.click(screen.getByText('My Document'));
    const input = document.querySelector('.topbar-title-input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.blur(input);
    const doc = useDocumentStore.getState().documents.find((d) => d.id === 'doc-1');
    expect(doc?.title).toBe('My Document');
  });

  it('renders the ExportMenu component', () => {
    render(<Topbar />);
    expect(screen.getByTestId('export-menu')).toBeInTheDocument();
  });

  it('renders the UserMenu component', () => {
    render(<Topbar />);
    expect(screen.getByTestId('user-menu')).toBeInTheDocument();
  });
});
