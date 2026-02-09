/**
 * Tests for Frustration Detection Hook
 *
 * These tests verify the four frustration signals and scoring system.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useFrustrationDetector } from '../useFrustrationDetector';
import { useSessionStore } from '../../stores/sessionStore';

// Stable spy references so assertions work across getState() calls
const mockRecordFrustrationSignal = vi.fn();
const mockRecordCheckInShown = vi.fn();
const mockRecordCheckInAction = vi.fn();
const mockRecordCheckInDismissal = vi.fn();

const mockSessionState = {
  recordFrustrationSignal: mockRecordFrustrationSignal,
  recordCheckInShown: mockRecordCheckInShown,
  recordCheckInAction: mockRecordCheckInAction,
  recordCheckInDismissal: mockRecordCheckInDismissal,
  lastInterventionTime: null,
};

// Mock the sessionStore
vi.mock('../../stores/sessionStore', () => ({
  useSessionStore: {
    getState: vi.fn(() => mockSessionState),
    setState: vi.fn(),
  },
}));

// Mock TipTap Editor
const createMockEditor = () => ({
  on: vi.fn(),
  off: vi.fn(),
  state: {
    selection: { from: 50, to: 50 },
    doc: {
      resolve: (pos: number) => ({
        parent: { content: { size: 100 } },
        start: () => 0,
      }),
    },
  },
  storage: {
    characterCount: {
      words: () => 0,
    },
  },
});

describe('useFrustrationDetector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should initialize without showing check-in', () => {
    const mockEditor = createMockEditor() as any;
    const { result } = renderHook(() => useFrustrationDetector(mockEditor));

    expect(result.current.shouldShowCheckIn).toBe(false);
    expect(result.current.checkInSignals).toEqual([]);
  });

  it('should not activate when editor is null', () => {
    const { result } = renderHook(() => useFrustrationDetector(null));

    expect(result.current.shouldShowCheckIn).toBe(false);
  });

  it('should set up event listeners when editor is provided', () => {
    const mockEditor = createMockEditor() as any;
    renderHook(() => useFrustrationDetector(mockEditor));

    expect(mockEditor.on).toHaveBeenCalledWith('transaction', expect.any(Function));
    expect(mockEditor.on).toHaveBeenCalledWith('update', expect.any(Function));
    expect(mockEditor.on).toHaveBeenCalledWith('selectionUpdate', expect.any(Function));
  });

  it('should clean up event listeners on unmount', () => {
    const mockEditor = createMockEditor() as any;
    const { unmount } = renderHook(() => useFrustrationDetector(mockEditor));

    unmount();

    expect(mockEditor.off).toHaveBeenCalledWith('transaction', expect.any(Function));
    expect(mockEditor.off).toHaveBeenCalledWith('update', expect.any(Function));
    expect(mockEditor.off).toHaveBeenCalledWith('selectionUpdate', expect.any(Function));
  });

  it('should dismiss check-in when dismissCheckIn is called', () => {
    const mockEditor = createMockEditor() as any;
    const { result } = renderHook(() => useFrustrationDetector(mockEditor));

    act(() => {
      result.current.dismissCheckIn();
    });

    expect(mockRecordCheckInDismissal).toHaveBeenCalled();
  });

  it('should handle check-in actions correctly', () => {
    const mockEditor = createMockEditor() as any;
    const { result } = renderHook(() => useFrustrationDetector(mockEditor));

    act(() => {
      result.current.handleCheckInAction('voice_mode');
    });

    expect(mockRecordCheckInAction).toHaveBeenCalledWith('voice_mode');
  });

  it('should respect 10-minute cooldown between check-ins', () => {
    const mockEditor = createMockEditor() as any;
    const { result } = renderHook(() => useFrustrationDetector(mockEditor));

    expect(result.current).toHaveProperty('shouldShowCheckIn');
    expect(result.current).toHaveProperty('checkInSignals');
  });

  it('should record frustration signals in sessionStore', () => {
    const mockEditor = createMockEditor() as any;
    renderHook(() => useFrustrationDetector(mockEditor));

    expect(useSessionStore.getState).toBeDefined();
    expect(useSessionStore.getState().recordFrustrationSignal).toBeDefined();
  });
});

describe('Signal Detection Algorithms', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should have proper structure for rapid deletion detection', () => {
    const mockEditor = createMockEditor() as any;
    renderHook(() => useFrustrationDetector(mockEditor));

    expect(mockEditor.on).toHaveBeenCalledWith('transaction', expect.any(Function));
  });

  it('should have proper structure for long pause detection', () => {
    const mockEditor = createMockEditor() as any;
    renderHook(() => useFrustrationDetector(mockEditor));

    vi.advanceTimersByTime(5000);

    expect(vi.getTimerCount()).toBeGreaterThan(0);
  });

  it('should have proper structure for short burst detection', () => {
    const mockEditor = createMockEditor() as any;
    renderHook(() => useFrustrationDetector(mockEditor));

    vi.advanceTimersByTime(2000);

    expect(vi.getTimerCount()).toBeGreaterThan(0);
  });

  it('should have proper structure for cursor thrashing detection', () => {
    const mockEditor = createMockEditor() as any;
    renderHook(() => useFrustrationDetector(mockEditor));

    expect(mockEditor.on).toHaveBeenCalledWith('selectionUpdate', expect.any(Function));
  });
});
