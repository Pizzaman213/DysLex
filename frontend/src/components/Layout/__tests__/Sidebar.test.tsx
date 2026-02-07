import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../Sidebar';
import { useSettingsStore } from '@/stores/settingsStore';

vi.mock('@/components/Layout/DocumentList', () => ({
  DocumentList: () => <div data-testid="document-list" />,
}));

const renderSidebar = () =>
  render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>,
  );

describe('Sidebar', () => {
  beforeEach(() => {
    useSettingsStore.setState({
      theme: 'cream',
      sidebarCollapsed: false,
      mindMapEnabled: true,
      draftModeEnabled: true,
      polishModeEnabled: true,
    });
  });

  it('renders with role="navigation"', () => {
    renderSidebar();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('shows all 4 mode links when all modes are enabled', () => {
    renderSidebar();
    expect(screen.getByTitle('Capture')).toBeInTheDocument();
    expect(screen.getByTitle('Mind Map')).toBeInTheDocument();
    expect(screen.getByTitle('Draft')).toBeInTheDocument();
    expect(screen.getByTitle('Polish')).toBeInTheDocument();
  });

  it('hides Mind Map link when mindMapEnabled is false', () => {
    useSettingsStore.setState({ mindMapEnabled: false });
    renderSidebar();
    expect(screen.queryByTitle('Mind Map')).not.toBeInTheDocument();
  });

  it('hides Draft link when draftModeEnabled is false', () => {
    useSettingsStore.setState({ draftModeEnabled: false });
    renderSidebar();
    expect(screen.queryByTitle('Draft')).not.toBeInTheDocument();
  });

  it('hides Polish link when polishModeEnabled is false', () => {
    useSettingsStore.setState({ polishModeEnabled: false });
    renderSidebar();
    expect(screen.queryByTitle('Polish')).not.toBeInTheDocument();
  });

  it('toggles sidebarCollapsed when the logo button is clicked', () => {
    renderSidebar();
    const toggleBtn = screen.getByLabelText('Collapse sidebar');
    fireEvent.click(toggleBtn);
    expect(useSettingsStore.getState().sidebarCollapsed).toBe(true);
  });

  it('sets theme to night when the Night theme button is clicked', () => {
    renderSidebar();
    const nightBtn = screen.getByLabelText('Switch to Night theme');
    fireEvent.click(nightBtn);
    expect(useSettingsStore.getState().theme).toBe('night');
  });

  it('has "collapsed" class when sidebarCollapsed is true', () => {
    useSettingsStore.setState({ sidebarCollapsed: true });
    renderSidebar();
    const aside = screen.getByRole('navigation');
    expect(aside.className).toContain('collapsed');
  });
});
