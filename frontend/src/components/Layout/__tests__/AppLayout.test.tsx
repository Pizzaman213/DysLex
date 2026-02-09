import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppLayout } from '../AppLayout';
import { useSettingsStore } from '@/stores/settingsStore';
import { useDocumentStore } from '@/stores/documentStore';
import { useUserStore } from '@/stores/userStore';

vi.mock('@/components/Layout/Topbar', () => ({
  Topbar: () => <div data-testid="topbar" />,
}));

vi.mock('@/components/Layout/Sidebar', () => ({
  Sidebar: () => <div data-testid="sidebar" />,
}));

vi.mock('@/components/Layout/AnimatedOutlet', () => ({
  AnimatedOutlet: () => <div data-testid="animated-outlet" />,
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
  resetSync: vi.fn(),
  flushPendingSync: vi.fn(),
}));

vi.mock('@/services/userScopedStorage', () => ({
  setStorageUserId: vi.fn(),
  rehydrateAllStores: vi.fn().mockResolvedValue(undefined),
  migrateGlobalToScoped: vi.fn(),
  createUserScopedStorage: vi.fn().mockReturnValue(undefined),
  registerScopedStore: vi.fn(),
}));

const renderLayout = () =>
  render(
    <MemoryRouter>
      <AppLayout />
    </MemoryRouter>,
  );

describe('AppLayout', () => {
  beforeEach(() => {
    useSettingsStore.setState({ sidebarCollapsed: false, loadFromBackend: vi.fn() });
    useUserStore.setState({
      user: { id: '11111111-1111-1111-1111-111111111111', email: 'test@test.com', name: 'Test' },
      isAuthenticated: true,
    });
  });

  it('renders the Topbar component', () => {
    renderLayout();
    expect(screen.getByTestId('topbar')).toBeInTheDocument();
  });

  it('renders the Sidebar component', () => {
    renderLayout();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('has sidebar-collapsed class when sidebarCollapsed is true', () => {
    useSettingsStore.setState({ sidebarCollapsed: true });
    const { container } = renderLayout();
    const appDiv = container.querySelector('.app');
    expect(appDiv?.className).toContain('sidebar-collapsed');
  });

  it('does not have sidebar-collapsed class when sidebarCollapsed is false', () => {
    useSettingsStore.setState({ sidebarCollapsed: false });
    const { container } = renderLayout();
    const appDiv = container.querySelector('.app');
    expect(appDiv?.className).not.toContain('sidebar-collapsed');
  });

  it('calls initializeFromServer on mount', async () => {
    const mockInit = vi.fn().mockResolvedValue(undefined);
    useDocumentStore.setState({ initializeFromServer: mockInit });
    renderLayout();
    await waitFor(() => {
      expect(mockInit).toHaveBeenCalledOnce();
    });
  });
});
