import { useSettingsStore } from '@/stores/settingsStore';
import type { PageType } from '@/types';

const PAGE_TYPE_OPTIONS: { value: PageType; label: string }[] = [
  { value: 'letter', label: 'Letter (8.5" × 11")' },
  { value: 'a4', label: 'A4 (210 × 297 mm)' },
  { value: 'legal', label: 'Legal (8.5" × 14")' },
  { value: 'a5', label: 'A5 (148 × 210 mm)' },
  { value: 'wide', label: 'Wide' },
];

export function PageTypeSelector() {
  const { pageType, setPageType } = useSettingsStore();

  return (
    <select
      className="setting-select"
      value={pageType}
      onChange={(e) => setPageType(e.target.value as PageType)}
      aria-label="Select page type"
    >
      {PAGE_TYPE_OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
