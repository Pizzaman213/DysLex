import { useEffect } from 'react';
import { useSettingsStore } from '@/stores/settingsStore';
import type { FontFamily } from '@/types';

const FONT_MAP: Record<FontFamily, string> = {
  OpenDyslexic: "'OpenDyslexic', sans-serif",
  AtkinsonHyperlegible: "'Atkinson Hyperlegible', sans-serif",
  LexieReadable: "'Lexie Readable', sans-serif",
  TimesNewRoman: "'Times New Roman', Times, serif",
  Calibri: "'Calibri', 'Carlito', sans-serif",
  system: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
};

export function useEditorTypography() {
  const font = useSettingsStore((s) => s.font);
  const fontSize = useSettingsStore((s) => s.fontSize);
  const lineSpacing = useSettingsStore((s) => s.lineSpacing);
  const letterSpacing = useSettingsStore((s) => s.letterSpacing);

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--editor-font-family', FONT_MAP[font]);
    root.style.setProperty('--editor-font-size', `${fontSize}px`);
    root.style.setProperty('--editor-line-height', String(lineSpacing));
    root.style.setProperty('--editor-letter-spacing', `${letterSpacing}em`);
  }, [font, fontSize, lineSpacing, letterSpacing]);
}
