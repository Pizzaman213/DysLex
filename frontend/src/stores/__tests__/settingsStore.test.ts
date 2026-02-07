import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useSettingsStore } from '../settingsStore';

vi.mock('@/services/api', () => ({
  api: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

import { api } from '@/services/api';

const DEFAULT_SETTINGS = {
  language: 'en' as const,
  mindMapEnabled: true,
  draftModeEnabled: true,
  polishModeEnabled: true,
  passiveLearning: true,
  aiCoaching: true,
  inlineCorrections: true,
  progressTracking: true,
  readAloud: true,
  theme: 'cream' as const,
  font: 'OpenDyslexic' as const,
  pageType: 'a4' as const,
  viewMode: 'paper' as const,
  zoom: 100,
  showZoom: false,
  pageNumbers: true,
  fontSize: 18,
  lineSpacing: 1.75,
  letterSpacing: 0.05,
  voiceEnabled: true,
  autoCorrect: true,
  focusMode: false,
  ttsSpeed: 1.0,
  correctionAggressiveness: 50,
  anonymizedDataCollection: false,
  cloudSync: false,
  developerMode: false,
};

describe('settingsStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSettingsStore.setState({
      ...DEFAULT_SETTINGS,
      isLoading: false,
      isSyncing: false,
      sidebarCollapsed: false,
    });
  });

  it('has correct default values', () => {
    const state = useSettingsStore.getState();
    expect(state.language).toBe('en');
    expect(state.theme).toBe('cream');
    expect(state.font).toBe('OpenDyslexic');
    expect(state.zoom).toBe(100);
    expect(state.fontSize).toBe(18);
    expect(state.lineSpacing).toBe(1.75);
    expect(state.letterSpacing).toBe(0.05);
    expect(state.ttsSpeed).toBe(1.0);
    expect(state.correctionAggressiveness).toBe(50);
    expect(state.cloudSync).toBe(false);
    expect(state.sidebarCollapsed).toBe(false);
    expect(state.isLoading).toBe(false);
    expect(state.isSyncing).toBe(false);
  });

  it('setTheme updates theme', () => {
    useSettingsStore.getState().setTheme('night');
    expect(useSettingsStore.getState().theme).toBe('night');
  });

  it('setFont updates font', () => {
    useSettingsStore.getState().setFont('AtkinsonHyperlegible');
    expect(useSettingsStore.getState().font).toBe('AtkinsonHyperlegible');
  });

  it('setLanguage updates language', () => {
    useSettingsStore.getState().setLanguage('es');
    expect(useSettingsStore.getState().language).toBe('es');
  });

  // --- Zoom clamping ---
  it('setZoom clamps below minimum to 25', () => {
    useSettingsStore.getState().setZoom(10);
    expect(useSettingsStore.getState().zoom).toBe(25);
  });

  it('setZoom clamps above maximum to 200', () => {
    useSettingsStore.getState().setZoom(300);
    expect(useSettingsStore.getState().zoom).toBe(200);
  });

  it('setZoom accepts value within range', () => {
    useSettingsStore.getState().setZoom(150);
    expect(useSettingsStore.getState().zoom).toBe(150);
  });

  // --- FontSize clamping ---
  it('setFontSize clamps below minimum to 8', () => {
    useSettingsStore.getState().setFontSize(2);
    expect(useSettingsStore.getState().fontSize).toBe(8);
  });

  it('setFontSize clamps above maximum to 72', () => {
    useSettingsStore.getState().setFontSize(100);
    expect(useSettingsStore.getState().fontSize).toBe(72);
  });

  // --- LineSpacing clamping ---
  it('setLineSpacing clamps below minimum to 1.5', () => {
    useSettingsStore.getState().setLineSpacing(1.0);
    expect(useSettingsStore.getState().lineSpacing).toBe(1.5);
  });

  it('setLineSpacing clamps above maximum to 2.0', () => {
    useSettingsStore.getState().setLineSpacing(3.0);
    expect(useSettingsStore.getState().lineSpacing).toBe(2.0);
  });

  // --- LetterSpacing clamping ---
  it('setLetterSpacing clamps below minimum to 0.05', () => {
    useSettingsStore.getState().setLetterSpacing(0.01);
    expect(useSettingsStore.getState().letterSpacing).toBe(0.05);
  });

  it('setLetterSpacing clamps above maximum to 0.12', () => {
    useSettingsStore.getState().setLetterSpacing(0.5);
    expect(useSettingsStore.getState().letterSpacing).toBe(0.12);
  });

  // --- TtsSpeed clamping ---
  it('setTtsSpeed clamps below minimum to 0.5', () => {
    useSettingsStore.getState().setTtsSpeed(0.1);
    expect(useSettingsStore.getState().ttsSpeed).toBe(0.5);
  });

  it('setTtsSpeed clamps above maximum to 2.0', () => {
    useSettingsStore.getState().setTtsSpeed(5.0);
    expect(useSettingsStore.getState().ttsSpeed).toBe(2.0);
  });

  // --- CorrectionAggressiveness clamping ---
  it('setCorrectionAggressiveness clamps below minimum to 0', () => {
    useSettingsStore.getState().setCorrectionAggressiveness(-10);
    expect(useSettingsStore.getState().correctionAggressiveness).toBe(0);
  });

  it('setCorrectionAggressiveness clamps above maximum to 100', () => {
    useSettingsStore.getState().setCorrectionAggressiveness(200);
    expect(useSettingsStore.getState().correctionAggressiveness).toBe(100);
  });

  // --- toggleSidebar ---
  it('toggleSidebar flips sidebarCollapsed', () => {
    expect(useSettingsStore.getState().sidebarCollapsed).toBe(false);
    useSettingsStore.getState().toggleSidebar();
    expect(useSettingsStore.getState().sidebarCollapsed).toBe(true);
    useSettingsStore.getState().toggleSidebar();
    expect(useSettingsStore.getState().sidebarCollapsed).toBe(false);
  });

  // --- Cloud sync ---
  it('setCloudSync(true) triggers syncToBackend', async () => {
    vi.mocked(api.updateSettings).mockResolvedValue({} as never);
    useSettingsStore.getState().setCloudSync(true);
    expect(useSettingsStore.getState().cloudSync).toBe(true);
    // syncToBackend is async, wait for it
    await vi.waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalled();
    });
  });

  it('syncToBackend skips when isSyncing is true', async () => {
    useSettingsStore.setState({ isSyncing: true });
    await useSettingsStore.getState().syncToBackend();
    expect(api.updateSettings).not.toHaveBeenCalled();
  });

  // --- loadFromBackend ---
  it('loadFromBackend sets isLoading, applies fetched data, then clears isLoading', async () => {
    const fetchedSettings = { theme: 'night', fontSize: 24 };
    vi.mocked(api.getSettings).mockResolvedValue({ data: fetchedSettings } as never);

    const promise = useSettingsStore.getState().loadFromBackend();
    expect(useSettingsStore.getState().isLoading).toBe(true);

    await promise;
    const state = useSettingsStore.getState();
    expect(state.isLoading).toBe(false);
    expect(state.theme).toBe('night');
    expect(state.fontSize).toBe(24);
  });

  it('loadFromBackend handles API error and clears isLoading', async () => {
    vi.mocked(api.getSettings).mockRejectedValue(new Error('Network error'));

    await useSettingsStore.getState().loadFromBackend();
    expect(useSettingsStore.getState().isLoading).toBe(false);
  });
});
