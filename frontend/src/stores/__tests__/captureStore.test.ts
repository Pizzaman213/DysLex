import { describe, it, expect, beforeEach } from 'vitest';
import { useCaptureStore } from '../captureStore';
import type { ThoughtCard, CapturePhase } from '../captureStore';

describe('captureStore', () => {
  beforeEach(() => {
    useCaptureStore.setState({ phase: 'idle', transcript: '', cards: [], error: null });
  });

  it('has correct default state', () => {
    const state = useCaptureStore.getState();
    expect(state.phase).toBe('idle');
    expect(state.transcript).toBe('');
    expect(state.cards).toEqual([]);
    expect(state.error).toBeNull();
  });

  it('setPhase updates phase to each valid value', () => {
    const phases: CapturePhase[] = ['idle', 'recording', 'transcribing', 'extracting', 'review'];
    for (const phase of phases) {
      useCaptureStore.getState().setPhase(phase);
      expect(useCaptureStore.getState().phase).toBe(phase);
    }
  });

  it('setTranscript updates transcript', () => {
    useCaptureStore.getState().setTranscript('Hello world');
    expect(useCaptureStore.getState().transcript).toBe('Hello world');
  });

  it('setCards sets cards array', () => {
    const cards: ThoughtCard[] = [
      { id: '1', title: 'Idea A', body: 'Body A' },
      { id: '2', title: 'Idea B', body: 'Body B' },
    ];
    useCaptureStore.getState().setCards(cards);
    expect(useCaptureStore.getState().cards).toEqual(cards);
  });

  it('setError sets error string', () => {
    useCaptureStore.getState().setError('Something went wrong');
    expect(useCaptureStore.getState().error).toBe('Something went wrong');
  });

  it('setError(null) clears error', () => {
    useCaptureStore.getState().setError('An error');
    useCaptureStore.getState().setError(null);
    expect(useCaptureStore.getState().error).toBeNull();
  });

  it('updateCard updates matching card by id, leaves others unchanged', () => {
    const cards: ThoughtCard[] = [
      { id: '1', title: 'Original A', body: 'Body A' },
      { id: '2', title: 'Original B', body: 'Body B' },
    ];
    useCaptureStore.getState().setCards(cards);
    useCaptureStore.getState().updateCard('1', { title: 'Updated A' });

    const updated = useCaptureStore.getState().cards;
    expect(updated[0]).toEqual({ id: '1', title: 'Updated A', body: 'Body A' });
    expect(updated[1]).toEqual({ id: '2', title: 'Original B', body: 'Body B' });
  });

  it('removeCard filters out card by id', () => {
    const cards: ThoughtCard[] = [
      { id: '1', title: 'A', body: 'Body A' },
      { id: '2', title: 'B', body: 'Body B' },
      { id: '3', title: 'C', body: 'Body C' },
    ];
    useCaptureStore.getState().setCards(cards);
    useCaptureStore.getState().removeCard('2');

    const remaining = useCaptureStore.getState().cards;
    expect(remaining).toHaveLength(2);
    expect(remaining.map((c) => c.id)).toEqual(['1', '3']);
  });

  it('reorderCards moves card from oldIndex to newIndex', () => {
    const cards: ThoughtCard[] = [
      { id: 'A', title: 'A', body: '' },
      { id: 'B', title: 'B', body: '' },
      { id: 'C', title: 'C', body: '' },
    ];
    useCaptureStore.getState().setCards(cards);
    // Move index 0 to index 2: [A,B,C] -> [B,C,A]
    useCaptureStore.getState().reorderCards(0, 2);

    const reordered = useCaptureStore.getState().cards;
    expect(reordered.map((c) => c.id)).toEqual(['B', 'C', 'A']);
  });

  it('reset returns to initial state', () => {
    useCaptureStore.getState().setPhase('recording');
    useCaptureStore.getState().setTranscript('Some text');
    useCaptureStore.getState().setCards([{ id: '1', title: 'T', body: 'B' }]);
    useCaptureStore.getState().setError('err');

    useCaptureStore.getState().reset();

    const state = useCaptureStore.getState();
    expect(state.phase).toBe('idle');
    expect(state.transcript).toBe('');
    expect(state.cards).toEqual([]);
    expect(state.error).toBeNull();
  });
});
