import type { PaperFormat } from '@/constants/paperFormats';
import type { FormatIssue } from '@/stores/formatStore';

interface CheckerSettings {
  pageType: string;
  font: string;
  fontSize: number;
  lineSpacing: number;
  pageNumbers: boolean;
}

interface CheckerFormatState {
  authorLastName: string;
  shortenedTitle: string;
  accessibilityOverride: boolean;
}

const DYSLEXIC_FONTS = ['OpenDyslexic', 'AtkinsonHyperlegible', 'LexieReadable'];

export function checkFormat(
  format: PaperFormat,
  settings: CheckerSettings,
  formatState: CheckerFormatState
): FormatIssue[] {
  const issues: FormatIssue[] = [];
  let issueIndex = 0;

  const addIssue = (
    ruleId: string,
    label: string,
    category: FormatIssue['category'],
    severity: FormatIssue['severity'],
    description: string,
    currentValue: string,
    expectedValue: string,
    canAutoFix: boolean
  ) => {
    issues.push({
      id: `${ruleId}-${issueIndex++}`,
      ruleId,
      label,
      category,
      severity,
      description,
      currentValue,
      expectedValue,
      canAutoFix,
    });
  };

  // Page type check
  if (settings.pageType !== 'letter') {
    addIssue(
      `${format.id}-page`,
      'Letter size paper',
      'margins',
      'error',
      `${format.name} requires 8.5" x 11" (letter) paper.`,
      settings.pageType.toUpperCase(),
      'Letter',
      true
    );
  }

  // Font check
  const isFontMatch = settings.font === format.fontFamily;
  if (!isFontMatch) {
    const isDyslexicFont = DYSLEXIC_FONTS.includes(settings.font);
    if (isDyslexicFont && formatState.accessibilityOverride) {
      addIssue(
        `${format.id}-font`,
        `Using ${settings.font} (accessibility)`,
        'font',
        'info',
        `You're using a dyslexic-friendly font in the editor. The export will use ${format.fontFamily === 'TimesNewRoman' ? 'Times New Roman' : format.fontFamily}.`,
        settings.font,
        format.fontFamily === 'TimesNewRoman' ? 'Times New Roman' : format.fontFamily,
        false
      );
    } else {
      addIssue(
        `${format.id}-font`,
        `Font: Times New Roman`,
        'font',
        'error',
        `${format.name} requires ${format.fontFamily === 'TimesNewRoman' ? 'Times New Roman' : format.fontFamily}.`,
        settings.font,
        format.fontFamily === 'TimesNewRoman' ? 'Times New Roman' : format.fontFamily,
        true
      );
    }
  }

  // Font size check
  if (settings.fontSize !== format.fontSize) {
    addIssue(
      `${format.id}-font-size`,
      `Font size ${format.fontSize}pt`,
      'font',
      'error',
      `${format.name} requires ${format.fontSize}pt font.`,
      `${settings.fontSize}pt`,
      `${format.fontSize}pt`,
      true
    );
  }

  // Line spacing check
  if (settings.lineSpacing !== format.lineSpacing) {
    addIssue(
      `${format.id}-spacing`,
      'Double-spaced',
      'spacing',
      'error',
      `${format.name} requires double spacing (${format.lineSpacing}).`,
      `${settings.lineSpacing}`,
      `${format.lineSpacing}`,
      true
    );
  }

  // Page numbers check
  if (!settings.pageNumbers) {
    addIssue(
      `${format.id}-page-numbers`,
      'Page numbers',
      'pageNumbers',
      'error',
      `${format.name} requires page numbers.`,
      'Off',
      'On',
      true
    );
  }

  // Running header checks
  if (format.runningHeaderType === 'lastname-page' && !formatState.authorLastName.trim()) {
    addIssue(
      `${format.id}-header`,
      'Author last name needed',
      'header',
      'warning',
      'MLA requires your last name in the running header. Enter it in the Format panel.',
      'Not set',
      'Your last name',
      false
    );
  }

  if (format.runningHeaderType === 'shortened-title' && !formatState.shortenedTitle.trim()) {
    addIssue(
      `${format.id}-header`,
      'Shortened title needed',
      'header',
      'warning',
      'APA requires a shortened title (running head) in ALL CAPS. Enter it in the Format panel.',
      'Not set',
      'SHORTENED TITLE',
      false
    );
  }

  return issues;
}
