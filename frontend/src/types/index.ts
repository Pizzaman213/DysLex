export type WritingMode = 'capture' | 'mindmap' | 'draft' | 'polish' | 'progress' | 'settings';
export type Theme = 'cream' | 'night' | 'blue-tint';
export type FontFamily = 'OpenDyslexic' | 'AtkinsonHyperlegible' | 'LexieReadable' | 'system';
export type SettingsTab = 'general' | 'appearance' | 'accessibility' | 'privacy' | 'docs';
export type Language = 'en' | 'es' | 'fr' | 'de';

export interface UserSettings {
  // General
  language: Language;

  // Appearance
  theme: Theme;
  font: FontFamily;
  fontSize: number;
  lineSpacing: number;
  letterSpacing: number;

  // Accessibility
  voiceEnabled: boolean;
  autoCorrect: boolean;
  focusMode: boolean;
  ttsSpeed: number;
  correctionAggressiveness: number;

  // Privacy
  anonymizedDataCollection: boolean;
  cloudSync: boolean;

  // Advanced
  developerMode: boolean;
}

export interface DocCategory {
  id: string;
  title: string;
  docs: DocSection[];
}

export interface DocSection {
  id: string;
  title: string;
  path: string;
  content: string;
}
