export type WritingMode = 'capture' | 'mindmap' | 'draft' | 'polish' | 'progress' | 'settings';
export type Theme = 'cream' | 'night' | 'blue-tint';
export type FontFamily = 'OpenDyslexic' | 'AtkinsonHyperlegible' | 'LexieReadable' | 'system' | 'TimesNewRoman' | 'Calibri';
export type PageType = 'a4' | 'letter' | 'a5' | 'legal' | 'wide';
export type ViewMode = 'paper' | 'continuous';
export type SettingsTab = 'general' | 'appearance' | 'accessibility' | 'privacy' | 'docs';
export type Language = 'en' | 'es' | 'fr' | 'de';
export type MicPermission = 'granted' | 'denied' | 'prompt' | 'unknown';
export type LLMProvider = 'nvidia_nim' | 'ollama' | 'vllm';

export interface UserSettings {
  // General
  language: Language;

  // Writing Modes
  mindMapEnabled: boolean;
  draftModeEnabled: boolean;
  polishModeEnabled: boolean;

  // AI Features
  passiveLearning: boolean;
  aiCoaching: boolean;
  inlineCorrections: boolean;

  // Tools
  progressTracking: boolean;
  readAloud: boolean;

  // Appearance
  theme: Theme;
  font: FontFamily;
  pageType: PageType;
  viewMode: ViewMode;
  zoom: number;
  showZoom: boolean;
  pageNumbers: boolean;
  fontSize: number;
  lineSpacing: number;
  letterSpacing: number;

  // Accessibility
  voiceEnabled: boolean;
  micPermission: MicPermission;
  autoCorrect: boolean;
  focusMode: boolean;
  ttsSpeed: number;
  correctionAggressiveness: number;

  // Privacy
  anonymizedDataCollection: boolean;
  cloudSync: boolean;

  // Advanced
  developerMode: boolean;

  // LLM Provider
  llmProvider: LLMProvider | null;
  llmBaseUrl: string | null;
  llmModel: string | null;
  llmApiKeyConfigured: boolean;
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
