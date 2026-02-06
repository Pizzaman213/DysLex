import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  theme: 'cream' | 'night';
  font: string;
  fontSize: number;
  lineSpacing: number;
  voiceEnabled: boolean;
  autoCorrect: boolean;
  setTheme: (theme: 'cream' | 'night') => void;
  setFont: (font: string) => void;
  setFontSize: (size: number) => void;
  setLineSpacing: (spacing: number) => void;
  setVoiceEnabled: (enabled: boolean) => void;
  setAutoCorrect: (enabled: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'cream',
      font: 'OpenDyslexic',
      fontSize: 18,
      lineSpacing: 1.5,
      voiceEnabled: true,
      autoCorrect: true,
      setTheme: (theme) => set({ theme }),
      setFont: (font) => set({ font }),
      setFontSize: (fontSize) => set({ fontSize }),
      setLineSpacing: (lineSpacing) => set({ lineSpacing }),
      setVoiceEnabled: (voiceEnabled) => set({ voiceEnabled }),
      setAutoCorrect: (autoCorrect) => set({ autoCorrect }),
    }),
    { name: 'dyslex-settings' }
  )
);
