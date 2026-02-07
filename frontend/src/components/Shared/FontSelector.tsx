import { useSettingsStore } from '@/stores/settingsStore';
import type { FontFamily } from '@/types';

const FONT_OPTIONS: { value: FontFamily; label: string }[] = [
  { value: 'OpenDyslexic', label: 'OpenDyslexic' },
  { value: 'AtkinsonHyperlegible', label: 'Atkinson Hyperlegible' },
  { value: 'LexieReadable', label: 'Lexie Readable' },
  { value: 'system', label: 'System Default' },
];

export function FontSelector() {
  const {
    font,
    setFont,
    fontSize,
    setFontSize,
    lineSpacing,
    setLineSpacing,
    letterSpacing,
    setLetterSpacing,
  } = useSettingsStore();

  return (
    <div className="font-selector">
      <div className="setting-row">
        <label htmlFor="font-select">Font</label>
        <select
          id="font-select"
          value={font}
          onChange={(e) => setFont(e.target.value as FontFamily)}
        >
          {FONT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="setting-row">
        <label htmlFor="font-size">Font Size</label>
        <input
          id="font-size"
          type="range"
          min="16"
          max="24"
          value={fontSize}
          onChange={(e) => setFontSize(Number(e.target.value))}
        />
        <span className="setting-value">{fontSize}px</span>
      </div>

      <div className="setting-row">
        <label htmlFor="line-spacing">Line Spacing</label>
        <input
          id="line-spacing"
          type="range"
          min="1.5"
          max="2.0"
          step="0.05"
          value={lineSpacing}
          onChange={(e) => setLineSpacing(Number(e.target.value))}
        />
        <span className="setting-value">{lineSpacing.toFixed(2)}</span>
      </div>

      <div className="setting-row">
        <label htmlFor="letter-spacing">Letter Spacing</label>
        <input
          id="letter-spacing"
          type="range"
          min="0.05"
          max="0.12"
          step="0.01"
          value={letterSpacing}
          onChange={(e) => setLetterSpacing(Number(e.target.value))}
        />
        <span className="setting-value">{letterSpacing.toFixed(2)}em</span>
      </div>

      <div
        className="font-preview"
        style={{
          fontFamily: 'var(--editor-font-family)',
          fontSize: 'var(--editor-font-size)',
          lineHeight: 'var(--editor-line-height)',
          letterSpacing: 'var(--editor-letter-spacing)',
        }}
        aria-label="Font preview"
      >
        The quick brown fox jumps over the lazy dog.
      </div>
    </div>
  );
}
