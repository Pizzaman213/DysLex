import { PAPER_FORMATS, type PaperFormatId } from '@/constants/paperFormats';
import type { FormatIssue } from '@/stores/formatStore';
import type { FontFamily, PageType, ViewMode } from '@/types';

export interface SettingsActions {
  setPageType: (pageType: PageType) => void;
  setFont: (font: FontFamily) => void;
  setFontSize: (size: number) => void;
  setLineSpacing: (spacing: number) => void;
  setPageNumbers: (enabled: boolean) => void;
  setViewMode: (mode: ViewMode) => void;
}

export function applyFormat(
  formatId: PaperFormatId,
  settings: SettingsActions,
  accessibilityOverride: boolean
): void {
  if (formatId === 'none') return;

  const format = PAPER_FORMATS[formatId];
  if (!format) return;

  settings.setPageType('letter' as PageType);
  settings.setFontSize(format.fontSize);
  settings.setLineSpacing(format.lineSpacing);
  settings.setPageNumbers(true);
  settings.setViewMode('paper' as ViewMode);

  if (!accessibilityOverride) {
    settings.setFont(format.fontFamily as FontFamily);
  }
}

export function applyFormatFix(
  issue: FormatIssue,
  settings: SettingsActions
): void {
  if (!issue.canAutoFix) return;

  switch (issue.category) {
    case 'margins':
      settings.setPageType('letter' as PageType);
      break;
    case 'font':
      if (issue.ruleId.endsWith('-font-size')) {
        settings.setFontSize(parseInt(issue.expectedValue, 10));
      } else {
        settings.setFont(issue.expectedValue === 'Times New Roman' ? 'TimesNewRoman' as FontFamily : issue.expectedValue as FontFamily);
      }
      break;
    case 'spacing':
      settings.setLineSpacing(parseFloat(issue.expectedValue));
      break;
    case 'pageNumbers':
      settings.setPageNumbers(true);
      break;
  }
}
