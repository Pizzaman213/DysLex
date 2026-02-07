import { describe, it, expect, beforeEach } from 'vitest';
import { usePolishStore } from '../polishStore';
import type { TrackedChange } from '../polishStore';

function makeSuggestion(overrides: Partial<TrackedChange> = {}): TrackedChange {
  return {
    id: 'sug-1',
    type: 'replace',
    start: 0,
    end: 5,
    text: 'fixed',
    original: 'fixde',
    category: 'spelling',
    explanation: 'Common letter reversal',
    ...overrides,
  };
}

describe('polishStore', () => {
  beforeEach(() => {
    usePolishStore.setState({ suggestions: [], isAnalyzing: false, activeSuggestion: null });
  });

  it('has correct default state', () => {
    const state = usePolishStore.getState();
    expect(state.suggestions).toEqual([]);
    expect(state.isAnalyzing).toBe(false);
    expect(state.activeSuggestion).toBeNull();
  });

  it('setSuggestions sets the array', () => {
    const suggestions = [
      makeSuggestion({ id: 'sug-1' }),
      makeSuggestion({ id: 'sug-2', category: 'grammar' }),
    ];
    usePolishStore.getState().setSuggestions(suggestions);
    expect(usePolishStore.getState().suggestions).toEqual(suggestions);
  });

  it('applySuggestion sets isApplied:true on matching suggestion only', () => {
    const suggestions = [
      makeSuggestion({ id: 'sug-1' }),
      makeSuggestion({ id: 'sug-2' }),
    ];
    usePolishStore.getState().setSuggestions(suggestions);

    usePolishStore.getState().applySuggestion('sug-1');

    const updated = usePolishStore.getState().suggestions;
    expect(updated[0].isApplied).toBe(true);
    expect(updated[1].isApplied).toBeUndefined();
  });

  it('dismissSuggestion sets isDismissed:true on matching suggestion only', () => {
    const suggestions = [
      makeSuggestion({ id: 'sug-1' }),
      makeSuggestion({ id: 'sug-2' }),
    ];
    usePolishStore.getState().setSuggestions(suggestions);

    usePolishStore.getState().dismissSuggestion('sug-2');

    const updated = usePolishStore.getState().suggestions;
    expect(updated[0].isDismissed).toBeUndefined();
    expect(updated[1].isDismissed).toBe(true);
  });

  it('clearSuggestions empties array and clears activeSuggestion', () => {
    usePolishStore.getState().setSuggestions([makeSuggestion()]);
    usePolishStore.getState().setActiveSuggestion('sug-1');

    usePolishStore.getState().clearSuggestions();

    const state = usePolishStore.getState();
    expect(state.suggestions).toEqual([]);
    expect(state.activeSuggestion).toBeNull();
  });

  it('setActiveSuggestion sets the id', () => {
    usePolishStore.getState().setActiveSuggestion('sug-42');
    expect(usePolishStore.getState().activeSuggestion).toBe('sug-42');
  });

  it('setActiveSuggestion(null) clears it', () => {
    usePolishStore.getState().setActiveSuggestion('sug-42');
    usePolishStore.getState().setActiveSuggestion(null);
    expect(usePolishStore.getState().activeSuggestion).toBeNull();
  });

  it('setIsAnalyzing updates boolean', () => {
    usePolishStore.getState().setIsAnalyzing(true);
    expect(usePolishStore.getState().isAnalyzing).toBe(true);

    usePolishStore.getState().setIsAnalyzing(false);
    expect(usePolishStore.getState().isAnalyzing).toBe(false);
  });
});
