import { useFormatStore } from '../../stores/formatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { FORMAT_LABELS, type PaperFormatId } from '../../constants/paperFormats';
import { applyFormat } from '../../utils/applyFormat';

const FORMAT_OPTIONS: PaperFormatId[] = ['none', 'mla', 'apa', 'chicago'];

export function FormatSelector() {
  const { activeFormat, setActiveFormat, accessibilityOverride } = useFormatStore();
  const settings = useSettingsStore();

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const formatId = e.target.value as PaperFormatId;
    setActiveFormat(formatId);

    if (formatId !== 'none') {
      applyFormat(formatId, settings, accessibilityOverride);
    }
  };

  return (
    <select
      className="editor-toolbar__select editor-toolbar__format-select"
      value={activeFormat}
      onChange={handleChange}
      aria-label="Paper format"
      title="Academic paper format"
    >
      {FORMAT_OPTIONS.map((id) => (
        <option key={id} value={id}>
          {FORMAT_LABELS[id]}
        </option>
      ))}
    </select>
  );
}
