import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useSessionStore } from '../sessionStore';

describe('sessionStore', () => {
  beforeEach(() => {
    useSessionStore.setState({
      startTime: null,
      totalWordsWritten: 0,
      correctionsApplied: 0,
      correctionsDismissed: 0,
      lastInterventionTime: null,
      frustrationEvents: [],
      checkInHistory: [],
      lastCheckInTime: null,
    });
  });

  it('has correct default state', () => {
    const state = useSessionStore.getState();
    expect(state.startTime).toBeNull();
    expect(state.totalWordsWritten).toBe(0);
    expect(state.correctionsApplied).toBe(0);
    expect(state.correctionsDismissed).toBe(0);
    expect(state.lastInterventionTime).toBeNull();
    expect(state.frustrationEvents).toEqual([]);
    expect(state.checkInHistory).toEqual([]);
    expect(state.lastCheckInTime).toBeNull();
  });

  it('startSession sets startTime and resets all counters', () => {
    // Pre-populate some data
    useSessionStore.setState({ totalWordsWritten: 50, correctionsApplied: 3 });

    useSessionStore.getState().startSession();

    const state = useSessionStore.getState();
    expect(state.startTime).not.toBeNull();
    expect(state.startTime).toBeTypeOf('number');
    expect(state.totalWordsWritten).toBe(0);
    expect(state.correctionsApplied).toBe(0);
    expect(state.correctionsDismissed).toBe(0);
    expect(state.lastInterventionTime).toBeNull();
    expect(state.frustrationEvents).toEqual([]);
    expect(state.checkInHistory).toEqual([]);
    expect(state.lastCheckInTime).toBeNull();
  });

  it('endSession clears all state', () => {
    useSessionStore.getState().startSession();
    useSessionStore.getState().incrementWords(10);
    useSessionStore.getState().recordCorrectionApplied();

    useSessionStore.getState().endSession();

    const state = useSessionStore.getState();
    expect(state.startTime).toBeNull();
    expect(state.totalWordsWritten).toBe(0);
    expect(state.correctionsApplied).toBe(0);
    expect(state.correctionsDismissed).toBe(0);
    expect(state.lastInterventionTime).toBeNull();
    expect(state.frustrationEvents).toEqual([]);
    expect(state.checkInHistory).toEqual([]);
    expect(state.lastCheckInTime).toBeNull();
  });

  it('incrementWords adds count to totalWordsWritten', () => {
    useSessionStore.getState().incrementWords(10);
    expect(useSessionStore.getState().totalWordsWritten).toBe(10);
  });

  it('incrementWords multiple times accumulates', () => {
    useSessionStore.getState().incrementWords(10);
    useSessionStore.getState().incrementWords(5);
    useSessionStore.getState().incrementWords(20);
    expect(useSessionStore.getState().totalWordsWritten).toBe(35);
  });

  it('recordCorrectionApplied increments correctionsApplied', () => {
    useSessionStore.getState().recordCorrectionApplied();
    useSessionStore.getState().recordCorrectionApplied();
    expect(useSessionStore.getState().correctionsApplied).toBe(2);
  });

  it('recordCorrectionDismissed increments correctionsDismissed', () => {
    useSessionStore.getState().recordCorrectionDismissed();
    useSessionStore.getState().recordCorrectionDismissed();
    useSessionStore.getState().recordCorrectionDismissed();
    expect(useSessionStore.getState().correctionsDismissed).toBe(3);
  });

  it('getTimeSpent returns 0 when no session is active', () => {
    expect(useSessionStore.getState().getTimeSpent()).toBe(0);
  });

  it('getTimeSpent returns minutes elapsed when session is active', () => {
    const fixedNow = 1700000000000;
    const spy = vi.spyOn(Date, 'now').mockReturnValue(fixedNow);

    // Set startTime to 5 minutes before fixedNow
    useSessionStore.setState({ startTime: fixedNow - 5 * 60000 });

    const minutes = useSessionStore.getState().getTimeSpent();
    expect(minutes).toBe(5);

    spy.mockRestore();
  });

  it('recordFrustrationSignal appends to frustrationEvents', () => {
    const signal = {
      type: 'rapid_deletion' as const,
      timestamp: Date.now(),
      severity: 0.8,
    };
    useSessionStore.getState().recordFrustrationSignal(signal);

    const events = useSessionStore.getState().frustrationEvents;
    expect(events).toHaveLength(1);
    expect(events[0]).toEqual(signal);

    const signal2 = {
      type: 'long_pause' as const,
      timestamp: Date.now(),
      severity: 0.5,
    };
    useSessionStore.getState().recordFrustrationSignal(signal2);
    expect(useSessionStore.getState().frustrationEvents).toHaveLength(2);
  });

  it('recordCheckInShown sets lastCheckInTime, lastInterventionTime, appends to checkInHistory', () => {
    const beforeCall = Date.now();
    useSessionStore.getState().recordCheckInShown(['rapid_deletion', 'long_pause']);

    const state = useSessionStore.getState();
    expect(state.lastCheckInTime).not.toBeNull();
    expect(state.lastCheckInTime).toBeGreaterThanOrEqual(beforeCall);
    expect(state.lastInterventionTime).not.toBeNull();
    expect(state.lastInterventionTime).toBeGreaterThanOrEqual(beforeCall);
    expect(state.checkInHistory).toHaveLength(1);
    expect(state.checkInHistory[0].signalTypes).toEqual(['rapid_deletion', 'long_pause']);
    expect(state.checkInHistory[0].action).toBeNull();
  });

  it('recordCheckInDismissal updates the last checkIn action to dismissed', () => {
    useSessionStore.getState().recordCheckInShown(['short_burst']);

    useSessionStore.getState().recordCheckInDismissal();

    const history = useSessionStore.getState().checkInHistory;
    expect(history).toHaveLength(1);
    expect(history[0].action).toBe('dismissed');
  });
});
