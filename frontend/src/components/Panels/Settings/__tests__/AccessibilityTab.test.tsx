import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AccessibilityTab } from '../AccessibilityTab';
import { useSettingsStore } from '@/stores/settingsStore';

vi.mock('@/services/api', () => ({ api: { getSettings: vi.fn(), updateSettings: vi.fn() } }));

beforeEach(() => {
  useSettingsStore.setState({
    ttsSpeed: 1.0,
    correctionAggressiveness: 50,
    developerMode: false,
    cloudSync: false,
  });
});

describe('AccessibilityTab', () => {
  it('TTS speed slider renders with value 1.0', () => {
    render(<AccessibilityTab />);
    const slider = document.getElementById('tts-speed-slider') as HTMLInputElement;
    expect(slider).toBeTruthy();
    expect(slider.value).toBe('1');
  });

  it('changing TTS speed slider updates store', () => {
    render(<AccessibilityTab />);
    const slider = document.getElementById('tts-speed-slider') as HTMLInputElement;
    fireEvent.change(slider, { target: { value: '1.5' } });
    expect(useSettingsStore.getState().ttsSpeed).toBe(1.5);
  });

  it('correction aggressiveness slider renders', () => {
    render(<AccessibilityTab />);
    const slider = document.getElementById('correction-aggressiveness-slider') as HTMLInputElement;
    expect(slider).toBeTruthy();
    expect(slider.value).toBe('50');
  });

  it('aggressiveness label shows "Light" for value 50', () => {
    render(<AccessibilityTab />);
    // Math.floor(50 / 33.34) = 1, aggressivenessLabels[1] = "Light"
    expect(screen.getByText(/Light/)).toBeInTheDocument();
  });

  it('Developer mode toggle click flips developerMode in store', () => {
    render(<AccessibilityTab />);
    const toggle = screen.getByRole('switch', { name: /developer mode/i });
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    fireEvent.click(toggle);
    expect(useSettingsStore.getState().developerMode).toBe(true);
  });
});
