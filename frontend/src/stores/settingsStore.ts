import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Theme, FontFamily, Language, UserSettings } from '@/types';
import { api } from '@/services/api';

interface SettingsState extends UserSettings {
  isLoading: boolean;
  isSyncing: boolean;

  // General setters
  setLanguage: (language: Language) => void;

  // Appearance setters
  setTheme: (theme: Theme) => void;
  setFont: (font: FontFamily) => void;
  setFontSize: (size: number) => void;
  setLineSpacing: (spacing: number) => void;
  setLetterSpacing: (spacing: number) => void;

  // Accessibility setters
  setVoiceEnabled: (enabled: boolean) => void;
  setAutoCorrect: (enabled: boolean) => void;
  setFocusMode: (enabled: boolean) => void;
  setTtsSpeed: (speed: number) => void;
  setCorrectionAggressiveness: (level: number) => void;

  // Privacy setters
  setAnonymizedDataCollection: (enabled: boolean) => void;
  setCloudSync: (enabled: boolean) => void;

  // Advanced setters
  setDeveloperMode: (enabled: boolean) => void;

  // Sync methods
  loadFromBackend: () => Promise<void>;
  syncToBackend: () => Promise<void>;
}

const DEFAULT_SETTINGS: UserSettings = {
  language: 'en',
  theme: 'cream',
  font: 'OpenDyslexic',
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

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_SETTINGS,
      isLoading: false,
      isSyncing: false,

      // General
      setLanguage: (language) => {
        set({ language });
        if (get().cloudSync) get().syncToBackend();
      },

      // Appearance
      setTheme: (theme) => {
        set({ theme });
        if (get().cloudSync) get().syncToBackend();
      },
      setFont: (font) => {
        set({ font });
        if (get().cloudSync) get().syncToBackend();
      },
      setFontSize: (size) => {
        set({ fontSize: Math.max(16, Math.min(24, size)) });
        if (get().cloudSync) get().syncToBackend();
      },
      setLineSpacing: (spacing) => {
        set({ lineSpacing: Math.max(1.5, Math.min(2.0, spacing)) });
        if (get().cloudSync) get().syncToBackend();
      },
      setLetterSpacing: (spacing) => {
        set({ letterSpacing: Math.max(0.05, Math.min(0.12, spacing)) });
        if (get().cloudSync) get().syncToBackend();
      },

      // Accessibility
      setVoiceEnabled: (voiceEnabled) => {
        set({ voiceEnabled });
        if (get().cloudSync) get().syncToBackend();
      },
      setAutoCorrect: (autoCorrect) => {
        set({ autoCorrect });
        if (get().cloudSync) get().syncToBackend();
      },
      setFocusMode: (focusMode) => {
        set({ focusMode });
        if (get().cloudSync) get().syncToBackend();
      },
      setTtsSpeed: (ttsSpeed) => {
        set({ ttsSpeed: Math.max(0.5, Math.min(2.0, ttsSpeed)) });
        if (get().cloudSync) get().syncToBackend();
      },
      setCorrectionAggressiveness: (correctionAggressiveness) => {
        set({ correctionAggressiveness: Math.max(0, Math.min(100, correctionAggressiveness)) });
        if (get().cloudSync) get().syncToBackend();
      },

      // Privacy
      setAnonymizedDataCollection: (anonymizedDataCollection) => {
        set({ anonymizedDataCollection });
        if (get().cloudSync) get().syncToBackend();
      },
      setCloudSync: (cloudSync) => {
        set({ cloudSync });
        // If enabling cloud sync, immediately sync current state
        if (cloudSync) {
          get().syncToBackend();
        }
      },

      // Advanced
      setDeveloperMode: (developerMode) => {
        set({ developerMode });
        if (get().cloudSync) get().syncToBackend();
      },

      // Load settings from backend
      loadFromBackend: async () => {
        set({ isLoading: true });
        try {
          // TODO: Get actual user ID from auth store
          const userId = 'demo-user-id';
          const response = await api.getSettings(userId);
          if (response.data) {
            set({ ...response.data, isLoading: false });
          }
        } catch (error) {
          console.error('Failed to load settings from backend:', error);
          set({ isLoading: false });
        }
      },

      // Sync settings to backend
      syncToBackend: async () => {
        const state = get();
        if (state.isSyncing) return; // Prevent concurrent syncs

        set({ isSyncing: true });
        try {
          // TODO: Get actual user ID from auth store
          const userId = 'demo-user-id';
          const settings: Partial<UserSettings> = {
            language: state.language,
            theme: state.theme,
            font: state.font,
            fontSize: state.fontSize,
            lineSpacing: state.lineSpacing,
            letterSpacing: state.letterSpacing,
            voiceEnabled: state.voiceEnabled,
            autoCorrect: state.autoCorrect,
            focusMode: state.focusMode,
            ttsSpeed: state.ttsSpeed,
            correctionAggressiveness: state.correctionAggressiveness,
            anonymizedDataCollection: state.anonymizedDataCollection,
            cloudSync: state.cloudSync,
            developerMode: state.developerMode,
          };
          await api.updateSettings(userId, settings);
          set({ isSyncing: false });
        } catch (error) {
          console.error('Failed to sync settings to backend:', error);
          set({ isSyncing: false });
        }
      },
    }),
    { name: 'dyslex-settings' }
  )
);
