import { describe, it, expect, beforeEach } from 'vitest';
import { useEditorStore } from '../editorStore';
import type { Correction } from '../editorStore';

const makeCorrectionFixtures = (): Correction[] => [
  {
    id: 'c1',
    original: 'teh',
    suggested: 'the',
    type: 'spelling',
    start: 0,
    end: 3,
    explanation: 'Common transposition',
  },
  {
    id: 'c2',
    original: 'becuase',
    suggested: 'because',
    type: 'phonetic',
    start: 10,
    end: 17,
  },
  {
    id: 'c3',
    original: 'there',
    suggested: 'their',
    type: 'homophone',
    start: 20,
    end: 25,
    explanation: 'Possessive form needed',
  },
];

describe('editorStore', () => {
  beforeEach(() => {
    useEditorStore.setState({
      content: '',
      corrections: [],
      isSaving: false,
      activeCorrection: null,
      editorInstance: null,
    });
  });

  it('has correct default state values', () => {
    const state = useEditorStore.getState();
    expect(state.content).toBe('');
    expect(state.corrections).toEqual([]);
    expect(state.isSaving).toBe(false);
    expect(state.activeCorrection).toBeNull();
    expect(state.editorInstance).toBeNull();
  });

  it('setContent updates content', () => {
    useEditorStore.getState().setContent('Hello world');
    expect(useEditorStore.getState().content).toBe('Hello world');
  });

  it('setCorrections sets corrections array', () => {
    const corrections = makeCorrectionFixtures();
    useEditorStore.getState().setCorrections(corrections);
    expect(useEditorStore.getState().corrections).toHaveLength(3);
    expect(useEditorStore.getState().corrections[0].id).toBe('c1');
  });

  it('clearCorrections empties corrections', () => {
    useEditorStore.getState().setCorrections(makeCorrectionFixtures());
    expect(useEditorStore.getState().corrections).toHaveLength(3);
    useEditorStore.getState().clearCorrections();
    expect(useEditorStore.getState().corrections).toEqual([]);
  });

  it('setIsSaving updates isSaving', () => {
    useEditorStore.getState().setIsSaving(true);
    expect(useEditorStore.getState().isSaving).toBe(true);
    useEditorStore.getState().setIsSaving(false);
    expect(useEditorStore.getState().isSaving).toBe(false);
  });

  it('applyCorrection sets isApplied:true on matching correction only', () => {
    useEditorStore.getState().setCorrections(makeCorrectionFixtures());
    useEditorStore.getState().applyCorrection('c2');

    const corrections = useEditorStore.getState().corrections;
    expect(corrections.find((c) => c.id === 'c2')?.isApplied).toBe(true);
    expect(corrections.find((c) => c.id === 'c1')?.isApplied).toBeUndefined();
    expect(corrections.find((c) => c.id === 'c3')?.isApplied).toBeUndefined();
  });

  it('applyCorrection with non-existent id does not change anything', () => {
    const corrections = makeCorrectionFixtures();
    useEditorStore.getState().setCorrections(corrections);
    useEditorStore.getState().applyCorrection('nonexistent');

    const result = useEditorStore.getState().corrections;
    expect(result).toHaveLength(3);
    result.forEach((c) => {
      expect(c.isApplied).toBeUndefined();
    });
  });

  it('dismissCorrection sets isDismissed:true on matching correction only', () => {
    useEditorStore.getState().setCorrections(makeCorrectionFixtures());
    useEditorStore.getState().dismissCorrection('c1');

    const corrections = useEditorStore.getState().corrections;
    expect(corrections.find((c) => c.id === 'c1')?.isDismissed).toBe(true);
    expect(corrections.find((c) => c.id === 'c2')?.isDismissed).toBeUndefined();
    expect(corrections.find((c) => c.id === 'c3')?.isDismissed).toBeUndefined();
  });

  it('applyAllCorrections marks all non-applied/non-dismissed as applied', () => {
    useEditorStore.getState().setCorrections(makeCorrectionFixtures());
    useEditorStore.getState().applyAllCorrections();

    const corrections = useEditorStore.getState().corrections;
    corrections.forEach((c) => {
      expect(c.isApplied).toBe(true);
    });
  });

  it('applyAllCorrections skips already-dismissed corrections', () => {
    useEditorStore.getState().setCorrections(makeCorrectionFixtures());
    useEditorStore.getState().dismissCorrection('c1');
    useEditorStore.getState().applyAllCorrections();

    const corrections = useEditorStore.getState().corrections;
    const c1 = corrections.find((c) => c.id === 'c1');
    expect(c1?.isDismissed).toBe(true);
    // Dismissed corrections should NOT get isApplied set
    expect(c1?.isApplied).toBeUndefined();

    const c2 = corrections.find((c) => c.id === 'c2');
    expect(c2?.isApplied).toBe(true);
  });

  it('setActiveCorrection sets the id', () => {
    useEditorStore.getState().setActiveCorrection('c1');
    expect(useEditorStore.getState().activeCorrection).toBe('c1');
  });

  it('setActiveCorrection(null) clears it', () => {
    useEditorStore.getState().setActiveCorrection('c1');
    expect(useEditorStore.getState().activeCorrection).toBe('c1');
    useEditorStore.getState().setActiveCorrection(null);
    expect(useEditorStore.getState().activeCorrection).toBeNull();
  });
});
