import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { PaperFormatId, RuleSeverity, RuleCategory } from '@/constants/paperFormats';

export interface FormatIssue {
  id: string;
  ruleId: string;
  label: string;
  category: RuleCategory;
  severity: RuleSeverity;
  description: string;
  currentValue: string;
  expectedValue: string;
  canAutoFix: boolean;
}

interface FormatState {
  activeFormat: PaperFormatId;
  documentFormats: Record<string, PaperFormatId>;
  issues: FormatIssue[];
  authorLastName: string;
  shortenedTitle: string;
  accessibilityOverride: boolean;

  setActiveFormat: (format: PaperFormatId) => void;
  setDocumentFormat: (docId: string, format: PaperFormatId) => void;
  getDocumentFormat: (docId: string) => PaperFormatId;
  setIssues: (issues: FormatIssue[]) => void;
  dismissIssue: (issueId: string) => void;
  setAuthorLastName: (name: string) => void;
  setShortenedTitle: (title: string) => void;
  setAccessibilityOverride: (override: boolean) => void;
}

export const useFormatStore = create<FormatState>()(
  persist(
    (set, get) => ({
      activeFormat: 'none',
      documentFormats: {},
      issues: [],
      authorLastName: '',
      shortenedTitle: '',
      accessibilityOverride: false,

      setActiveFormat: (format) => set({ activeFormat: format, issues: [] }),

      setDocumentFormat: (docId, format) =>
        set((s) => ({
          documentFormats: { ...s.documentFormats, [docId]: format },
        })),

      getDocumentFormat: (docId) => get().documentFormats[docId] || 'none',

      setIssues: (issues) => set({ issues }),

      dismissIssue: (issueId) =>
        set((s) => ({
          issues: s.issues.filter((i) => i.id !== issueId),
        })),

      setAuthorLastName: (name) => set({ authorLastName: name }),

      setShortenedTitle: (title) => set({ shortenedTitle: title }),

      setAccessibilityOverride: (override) => set({ accessibilityOverride: override }),
    }),
    {
      name: 'dyslex-format',
      partialize: (state) => ({
        documentFormats: state.documentFormats,
        authorLastName: state.authorLastName,
        shortenedTitle: state.shortenedTitle,
        accessibilityOverride: state.accessibilityOverride,
      }),
    }
  )
);
