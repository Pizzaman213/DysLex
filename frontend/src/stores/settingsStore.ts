import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Theme, FontFamily, PageType, ViewMode, Language, MicPermission, UserSettings } from '@/types';
import { api } from '@/services/api';

interface SettingsState extends UserSettings {
  isLoading: boolean;
  isSyncing: boolean;
  sidebarCollapsed: boolean;

  // UI actions
  toggleSidebar: () => void;

  // General setters
  setLanguage: (language: Language) => void;

  // Writing Mode setters
  setMindMapEnabled: (enabled: boolean) => void;
  setDraftModeEnabled: (enabled: boolean) => void;
  setPolishModeEnabled: (enabled: boolean) => void;

  // AI Feature setters
  setPassiveLearning: (enabled: boolean) => void;
  setAiCoaching: (enabled: boolean) => void;
  setInlineCorrections: (enabled: boolean) => void;

  // Tool setters
  setProgressTracking: (enabled: boolean) => void;
  setReadAloud: (enabled: boolean) => void;

  // Appearance setters
  setTheme: (theme: Theme) => void;
  setFont: (font: FontFamily) => void;
  setPageType: (pageType: PageType) => void;
  setViewMode: (viewMode: ViewMode) => void;
  setZoom: (zoom: number) => void;
  setShowZoom: (show: boolean) => void;
  setPageNumbers: (enabled: boolean) => void;
  togglePageNumbers: () => void;
  setFontSize: (size: number) => void;
  setLineSpacing: (spacing: number) => void;
  setLetterSpacing: (spacing: number) => void;

  // Accessibility setters
  setVoiceEnabled: (enabled: boolean) => void;
  setMicPermission: (micPermission: MicPermission) => void;
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
  mindMapEnabled: true,
  draftModeEnabled: true,
  polishModeEnabled: true,
  passiveLearning: true,
  aiCoaching: true,
  inlineCorrections: true,
  progressTracking: true,
  readAloud: true,
  theme: 'cream',
  font: 'OpenDyslexic',
  pageType: 'a4',
  viewMode: 'paper',
  zoom: 100,
  showZoom: false,
  pageNumbers: true,
  fontSize: 18,
  lineSpacing: 1.75,
  letterSpacing: 0.05,
  voiceEnabled: true,
  micPermission: 'unknown',
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
      sidebarCollapsed: false,

      // UI actions
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

      // General
      setLanguage: (language) => {
        set({ language });
        if (get().cloudSync) get().syncToBackend();
      },

      // Writing Modes
      setMindMapEnabled: (mindMapEnabled) => {
        set({ mindMapEnabled });
        if (get().cloudSync) get().syncToBackend();
      },
      setDraftModeEnabled: (draftModeEnabled) => {
        set({ draftModeEnabled });
        if (get().cloudSync) get().syncToBackend();
      },
      setPolishModeEnabled: (polishModeEnabled) => {
        set({ polishModeEnabled });
        if (get().cloudSync) get().syncToBackend();
      },

      // AI Features
      setPassiveLearning: (passiveLearning) => {
        set({ passiveLearning });
        if (get().cloudSync) get().syncToBackend();
      },
      setAiCoaching: (aiCoaching) => {
        set({ aiCoaching });
        if (get().cloudSync) get().syncToBackend();
      },
      setInlineCorrections: (inlineCorrections) => {
        set({ inlineCorrections });
        if (get().cloudSync) get().syncToBackend();
      },

      // Tools
      setProgressTracking: (progressTracking) => {
        set({ progressTracking });
        if (get().cloudSync) get().syncToBackend();
      },
      setReadAloud: (readAloud) => {
        set({ readAloud });
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
      setPageType: (pageType) => {
        set({ pageType });
        if (get().cloudSync) get().syncToBackend();
      },
      setViewMode: (viewMode) => {
        set({ viewMode });
        if (get().cloudSync) get().syncToBackend();
      },
      setZoom: (zoom) => {
        set({ zoom: Math.max(25, Math.min(200, zoom)) });
        if (get().cloudSync) get().syncToBackend();
      },
      setShowZoom: (showZoom) => {
        set({ showZoom });
        if (get().cloudSync) get().syncToBackend();
      },
      setPageNumbers: (pageNumbers) => {
        set({ pageNumbers });
        if (get().cloudSync) get().syncToBackend();
      },
      togglePageNumbers: () => {
        set((s) => ({ pageNumbers: !s.pageNumbers }));
        if (get().cloudSync) get().syncToBackend();
      },
      setFontSize: (size) => {
        set({ fontSize: Math.max(8, Math.min(72, size)) });
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
      setMicPermission: (micPermission) => {
        set({ micPermission });
        // No syncToBackend — mic permission is per-browser/device
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
          const userId = '00000000-0000-0000-0000-000000000000';
          const response = await api.getSettings(userId);
          if (response.data) {
            set({ ...response.data, isLoading: false });
          } else {
            set({ isLoading: false });
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
          const userId = '00000000-0000-0000-0000-000000000000';
          const settings: Partial<UserSettings> = {
            language: state.language,
            mindMapEnabled: state.mindMapEnabled,
            draftModeEnabled: state.draftModeEnabled,
            polishModeEnabled: state.polishModeEnabled,
            passiveLearning: state.passiveLearning,
            aiCoaching: state.aiCoaching,
            inlineCorrections: state.inlineCorrections,
            progressTracking: state.progressTracking,
            readAloud: state.readAloud,
            theme: state.theme,
            font: state.font,
            pageType: state.pageType,
            viewMode: state.viewMode,
            zoom: state.zoom,
            showZoom: state.showZoom,
            pageNumbers: state.pageNumbers,
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
    {
      name: 'dyslex-settings',
      version: 2,
      migrate: (persisted, version) => {
        const state = persisted as Record<string, unknown>;
        if (version < 1) {
          state.pageNumbers = true;
        }
        if (version < 2) {
          state.micPermission = 'unknown';
        }
        return state as unknown as SettingsState;
      },
      merge: (persisted, current) => ({
        ...current,
        ...(persisted as Partial<SettingsState>),
      }),
    }
  )
);
