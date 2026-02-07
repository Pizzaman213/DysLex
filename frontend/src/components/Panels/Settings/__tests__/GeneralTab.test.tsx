import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GeneralTab } from '../GeneralTab';
import { useSettingsStore } from '@/stores/settingsStore';

vi.mock('@/services/api', () => ({ api: { getSettings: vi.fn(), updateSettings: vi.fn() } }));

beforeEach(() => {
  useSettingsStore.setState({
    language: 'en',
    mindMapEnabled: true,
    draftModeEnabled: true,
    polishModeEnabled: true,
    voiceEnabled: true,
    passiveLearning: true,
    aiCoaching: true,
    inlineCorrections: true,
    progressTracking: true,
    readAloud: true,
    autoCorrect: true,
    focusMode: false,
    cloudSync: false,
  });
});

describe('GeneralTab', () => {
  it('renders language dropdown with 4 options', () => {
    render(<GeneralTab />);
    const select = screen.getByLabelText(/display language/i);
    const options = select.querySelectorAll('option');
    expect(options).toHaveLength(4);
    expect(options[0]).toHaveTextContent('English');
    expect(options[1]).toHaveTextContent('Espanol');
    expect(options[2]).toHaveTextContent('Francais');
    expect(options[3]).toHaveTextContent('Deutsch');
  });

  it('changing language to "es" updates the store', () => {
    render(<GeneralTab />);
    const select = screen.getByLabelText(/display language/i);
    fireEvent.change(select, { target: { value: 'es' } });
    expect(useSettingsStore.getState().language).toBe('es');
  });

  it('Mind Map toggle click flips mindMapEnabled in store', () => {
    render(<GeneralTab />);
    const toggle = screen.getByRole('switch', { name: /mind map/i });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    fireEvent.click(toggle);
    expect(useSettingsStore.getState().mindMapEnabled).toBe(false);
  });

  it('Draft Mode toggle click flips draftModeEnabled in store', () => {
    render(<GeneralTab />);
    const toggle = document.getElementById('draft-toggle') as HTMLButtonElement;
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    fireEvent.click(toggle);
    expect(useSettingsStore.getState().draftModeEnabled).toBe(false);
  });

  it('Polish Mode toggle click flips polishModeEnabled in store', () => {
    render(<GeneralTab />);
    const toggle = screen.getByRole('switch', { name: /polish mode/i });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    fireEvent.click(toggle);
    expect(useSettingsStore.getState().polishModeEnabled).toBe(false);
  });

  it('Auto-Correct toggle click flips autoCorrect in store', () => {
    render(<GeneralTab />);
    const toggle = screen.getByRole('switch', { name: /auto-correct/i });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    fireEvent.click(toggle);
    expect(useSettingsStore.getState().autoCorrect).toBe(false);
  });

  it('Inline Corrections toggle is aria-checked="true" when enabled', () => {
    render(<GeneralTab />);
    const toggle = screen.getByRole('switch', { name: /inline corrections/i });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
  });

  it('Voice Input toggle click flips voiceEnabled in store', () => {
    render(<GeneralTab />);
    const toggle = screen.getByRole('switch', { name: /voice input/i });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    fireEvent.click(toggle);
    expect(useSettingsStore.getState().voiceEnabled).toBe(false);
  });
});
