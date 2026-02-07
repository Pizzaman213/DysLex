import { useSettingsStore } from '@/stores/settingsStore';
import type { FontFamily } from '@/types';

const FONT_OPTIONS: { value: FontFamily; label: string }[] = [
  { value: 'OpenDyslexic', label: 'OpenDyslexic' },
  { value: 'AtkinsonHyperlegible', label: 'Atkinson Hyperlegible' },
  { value: 'LexieReadable', label: 'Lexie Readable' },
  { value: 'system', label: 'System Default' },
];

export function FontSelector() {
  const { font, setFont } = useSettingsStore();

  return (
    <select
      id="font-select"
      value={font}
      onChange={(e) => setFont(e.target.value as FontFamily)}
      className="setting-select"
    >
      {FONT_OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
