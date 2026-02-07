import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AppearanceTab } from '../AppearanceTab';
import { useSettingsStore } from '@/stores/settingsStore';

vi.mock('@/components/Shared/ThemeSwitcher', () => ({
  ThemeSwitcher: () => <div data-testid="theme-switcher" />,
}));
vi.mock('@/components/Shared/FontSelector', () => ({
  FontSelector: () => <div data-testid="font-selector" />,
}));
vi.mock('@/components/Shared/PageTypeSelector', () => ({
  PageTypeSelector: () => <div data-testid="page-type-selector" />,
}));
vi.mock('@/services/api', () => ({ api: { getSettings: vi.fn(), updateSettings: vi.fn() } }));

beforeEach(() => {
  useSettingsStore.setState({
    viewMode: 'paper',
    showZoom: false,
    pageNumbers: true,
    fontSize: 18,
    lineSpacing: 1.75,
    letterSpacing: 0.05,
    cloudSync: false,
  });
});

describe('AppearanceTab', () => {
  it('renders ThemeSwitcher and FontSelector components', () => {
    render(<AppearanceTab />);
    expect(screen.getByTestId('theme-switcher')).toBeInTheDocument();
    expect(screen.getByTestId('font-selector')).toBeInTheDocument();
  });

  it('font size slider has correct min/max attributes', () => {
    render(<AppearanceTab />);
    const slider = document.getElementById('font-size-slider') as HTMLInputElement;
    expect(slider).toBeTruthy();
    expect(slider.min).toBe('8');
    expect(slider.max).toBe('72');
    expect(slider.step).toBe('1');
  });

  it('changing font size slider updates store', () => {
    render(<AppearanceTab />);
    const slider = document.getElementById('font-size-slider') as HTMLInputElement;
    fireEvent.change(slider, { target: { value: '24' } });
    expect(useSettingsStore.getState().fontSize).toBe(24);
  });

  it('line spacing slider has correct min/max', () => {
    render(<AppearanceTab />);
    const slider = document.getElementById('line-spacing-slider') as HTMLInputElement;
    expect(slider).toBeTruthy();
    expect(slider.min).toBe('1.5');
    expect(slider.max).toBe('2.0');
    expect(slider.step).toBe('0.05');
  });

  it('letter spacing slider has correct min/max', () => {
    render(<AppearanceTab />);
    const slider = document.getElementById('letter-spacing-slider') as HTMLInputElement;
    expect(slider).toBeTruthy();
    expect(slider.min).toBe('0.05');
    expect(slider.max).toBe('0.12');
    expect(slider.step).toBe('0.01');
  });

  it('view mode selector changes value in store', () => {
    render(<AppearanceTab />);
    const select = document.getElementById('view-mode-selector') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: 'continuous' } });
    expect(useSettingsStore.getState().viewMode).toBe('continuous');
  });
});
