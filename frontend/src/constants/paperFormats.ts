export type PaperFormatId = 'none' | 'mla' | 'apa' | 'chicago';

export type RuleSeverity = 'error' | 'warning' | 'info';
export type RuleCategory = 'margins' | 'font' | 'spacing' | 'indentation' | 'headings' | 'pageNumbers' | 'header';

export interface FormatRule {
  id: string;
  label: string;
  category: RuleCategory;
  severity: RuleSeverity;
  description: string;
}

export interface PaperFormat {
  id: PaperFormatId;
  name: string;
  shortName: string;
  fontFamily: string;
  fontFamilyCss: string;
  fontSize: number;
  lineSpacing: number;
  margins: string;
  firstLineIndent: string;
  pageNumberPosition: 'top-right' | 'bottom-center';
  runningHeaderType: 'lastname-page' | 'shortened-title' | 'page-only';
  rules: FormatRule[];
}

export const PAPER_FORMATS: Record<Exclude<PaperFormatId, 'none'>, PaperFormat> = {
  mla: {
    id: 'mla',
    name: 'MLA 9th Edition',
    shortName: 'MLA',
    fontFamily: 'TimesNewRoman',
    fontFamilyCss: "'Times New Roman', Times, serif",
    fontSize: 12,
    lineSpacing: 2.0,
    margins: '1in',
    firstLineIndent: '0.5in',
    pageNumberPosition: 'top-right',
    runningHeaderType: 'lastname-page',
    rules: [
      { id: 'mla-page', label: 'Letter size paper', category: 'margins', severity: 'error', description: 'MLA requires 8.5" x 11" (letter) paper.' },
      { id: 'mla-font', label: 'Times New Roman 12pt', category: 'font', severity: 'error', description: 'MLA requires a readable font like Times New Roman at 12pt.' },
      { id: 'mla-font-size', label: 'Font size 12pt', category: 'font', severity: 'error', description: 'Font size must be 12pt.' },
      { id: 'mla-spacing', label: 'Double-spaced', category: 'spacing', severity: 'error', description: 'MLA requires double spacing (2.0) throughout.' },
      { id: 'mla-indent', label: 'First-line indent 0.5"', category: 'indentation', severity: 'warning', description: 'Paragraphs should have a 0.5-inch first-line indent.' },
      { id: 'mla-page-numbers', label: 'Page numbers', category: 'pageNumbers', severity: 'error', description: 'Page numbers required in upper-right corner.' },
      { id: 'mla-header', label: 'Running header (Last Name + Page)', category: 'header', severity: 'warning', description: 'Running header with last name and page number in the upper-right corner.' },
    ],
  },
  apa: {
    id: 'apa',
    name: 'APA 7th Edition',
    shortName: 'APA',
    fontFamily: 'TimesNewRoman',
    fontFamilyCss: "'Times New Roman', Times, serif",
    fontSize: 12,
    lineSpacing: 2.0,
    margins: '1in',
    firstLineIndent: '0.5in',
    pageNumberPosition: 'top-right',
    runningHeaderType: 'shortened-title',
    rules: [
      { id: 'apa-page', label: 'Letter size paper', category: 'margins', severity: 'error', description: 'APA requires 8.5" x 11" (letter) paper.' },
      { id: 'apa-font', label: 'Times New Roman 12pt', category: 'font', severity: 'error', description: 'APA recommends Times New Roman 12pt (or Calibri 11pt).' },
      { id: 'apa-font-size', label: 'Font size 12pt', category: 'font', severity: 'error', description: 'Font size must be 12pt (or 11pt for Calibri).' },
      { id: 'apa-spacing', label: 'Double-spaced', category: 'spacing', severity: 'error', description: 'APA requires double spacing (2.0) throughout.' },
      { id: 'apa-indent', label: 'First-line indent 0.5"', category: 'indentation', severity: 'warning', description: 'Paragraphs should have a 0.5-inch first-line indent.' },
      { id: 'apa-page-numbers', label: 'Page numbers', category: 'pageNumbers', severity: 'error', description: 'Page numbers required in upper-right corner.' },
      { id: 'apa-header', label: 'Running head (shortened title)', category: 'header', severity: 'warning', description: 'Running head with shortened title in ALL CAPS on the left and page number on the right.' },
    ],
  },
  chicago: {
    id: 'chicago',
    name: 'Chicago (Notes & Bib)',
    shortName: 'Chicago',
    fontFamily: 'TimesNewRoman',
    fontFamilyCss: "'Times New Roman', Times, serif",
    fontSize: 12,
    lineSpacing: 2.0,
    margins: '1in',
    firstLineIndent: '0.5in',
    pageNumberPosition: 'top-right',
    runningHeaderType: 'page-only',
    rules: [
      { id: 'chi-page', label: 'Letter size paper', category: 'margins', severity: 'error', description: 'Chicago requires 8.5" x 11" (letter) paper.' },
      { id: 'chi-font', label: 'Times New Roman 12pt', category: 'font', severity: 'error', description: 'Chicago recommends Times New Roman at 12pt.' },
      { id: 'chi-font-size', label: 'Font size 12pt', category: 'font', severity: 'error', description: 'Font size must be 12pt.' },
      { id: 'chi-spacing', label: 'Double-spaced', category: 'spacing', severity: 'error', description: 'Chicago requires double spacing (2.0) throughout.' },
      { id: 'chi-indent', label: 'First-line indent 0.5"', category: 'indentation', severity: 'warning', description: 'Paragraphs should have a 0.5-inch first-line indent.' },
      { id: 'chi-page-numbers', label: 'Page numbers', category: 'pageNumbers', severity: 'error', description: 'Page numbers required (top-right, or bottom-center on first page).' },
    ],
  },
};

export const FORMAT_LABELS: Record<PaperFormatId, string> = {
  none: 'None',
  mla: 'MLA',
  apa: 'APA',
  chicago: 'Chicago',
};
