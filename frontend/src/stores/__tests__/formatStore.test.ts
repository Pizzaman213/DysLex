import { describe, it, expect, beforeEach } from 'vitest';
import { useFormatStore } from '../formatStore';
import type { FormatIssue } from '../formatStore';

describe('formatStore', () => {
  beforeEach(() => {
    useFormatStore.setState({
      activeFormat: 'none',
      documentFormats: {},
      issues: [],
      authorLastName: '',
      shortenedTitle: '',
      accessibilityOverride: false,
    });
  });

  it('has correct default state', () => {
    const state = useFormatStore.getState();
    expect(state.activeFormat).toBe('none');
    expect(state.documentFormats).toEqual({});
    expect(state.issues).toEqual([]);
    expect(state.authorLastName).toBe('');
    expect(state.shortenedTitle).toBe('');
    expect(state.accessibilityOverride).toBe(false);
  });

  it('setActiveFormat sets format and clears issues', () => {
    const issues: FormatIssue[] = [
      {
        id: 'i1', ruleId: 'r1', label: 'Font size',
        category: 'font', severity: 'error',
        description: 'Wrong font size', currentValue: '11pt',
        expectedValue: '12pt', canAutoFix: true,
      },
    ];
    useFormatStore.getState().setIssues(issues);
    expect(useFormatStore.getState().issues).toHaveLength(1);

    useFormatStore.getState().setActiveFormat('apa');
    expect(useFormatStore.getState().activeFormat).toBe('apa');
    expect(useFormatStore.getState().issues).toEqual([]);
  });

  it('setDocumentFormat sets format for specific document', () => {
    useFormatStore.getState().setDocumentFormat('doc-1', 'mla');
    useFormatStore.getState().setDocumentFormat('doc-2', 'chicago');

    const state = useFormatStore.getState();
    expect(state.documentFormats['doc-1']).toBe('mla');
    expect(state.documentFormats['doc-2']).toBe('chicago');
  });

  it('getDocumentFormat returns format or none for unknown doc', () => {
    useFormatStore.getState().setDocumentFormat('doc-1', 'apa');

    expect(useFormatStore.getState().getDocumentFormat('doc-1')).toBe('apa');
    expect(useFormatStore.getState().getDocumentFormat('unknown')).toBe('none');
  });

  it('setIssues replaces all issues', () => {
    const issues: FormatIssue[] = [
      {
        id: 'i1', ruleId: 'r1', label: 'Margins',
        category: 'font', severity: 'warning',
        description: 'Margins too narrow', currentValue: '0.5in',
        expectedValue: '1in', canAutoFix: true,
      },
      {
        id: 'i2', ruleId: 'r2', label: 'Spacing',
        category: 'font', severity: 'error',
        description: 'Wrong spacing', currentValue: '1.0',
        expectedValue: '2.0', canAutoFix: true,
      },
    ];
    useFormatStore.getState().setIssues(issues);
    expect(useFormatStore.getState().issues).toHaveLength(2);
  });

  it('dismissIssue removes issue by id', () => {
    const issues: FormatIssue[] = [
      {
        id: 'i1', ruleId: 'r1', label: 'A',
        category: 'font', severity: 'warning',
        description: '', currentValue: '', expectedValue: '',
        canAutoFix: false,
      },
      {
        id: 'i2', ruleId: 'r2', label: 'B',
        category: 'font', severity: 'error',
        description: '', currentValue: '', expectedValue: '',
        canAutoFix: false,
      },
    ];
    useFormatStore.getState().setIssues(issues);
    useFormatStore.getState().dismissIssue('i1');

    const remaining = useFormatStore.getState().issues;
    expect(remaining).toHaveLength(1);
    expect(remaining[0].id).toBe('i2');
  });

  it('setAuthorLastName updates author last name', () => {
    useFormatStore.getState().setAuthorLastName('Smith');
    expect(useFormatStore.getState().authorLastName).toBe('Smith');
  });

  it('setShortenedTitle updates shortened title', () => {
    useFormatStore.getState().setShortenedTitle('My Paper');
    expect(useFormatStore.getState().shortenedTitle).toBe('My Paper');
  });

  it('setAccessibilityOverride updates override flag', () => {
    useFormatStore.getState().setAccessibilityOverride(true);
    expect(useFormatStore.getState().accessibilityOverride).toBe(true);
    useFormatStore.getState().setAccessibilityOverride(false);
    expect(useFormatStore.getState().accessibilityOverride).toBe(false);
  });
});
