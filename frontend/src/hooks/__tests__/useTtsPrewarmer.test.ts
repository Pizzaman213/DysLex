import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTtsPrewarmer } from '../useTtsPrewarmer';
import { api } from '@/services/api';
import { sentenceAudioCache, findUncachedSentences } from '@/services/ttsSentenceCache';

vi.mock('@/services/api');

const mockFindUncached = vi.fn();
vi.mock('@/services/ttsSentenceCache', () => ({
  splitIntoSentences: (text: string) =>
    text.trim() ? text.split(/[.!?]+\s*/).filter(Boolean) : [],
  hashSentence: async (_text: string, _voice: string) => 'mock-hash',
  findUncachedSentences: (...args: any[]) => mockFindUncached(...args),
  sentenceAudioCache: {
    has: vi.fn(() => false),
    get: vi.fn(() => undefined),
    set: vi.fn(),
    clear: vi.fn(),
    size: 0,
  },
}));

function makeEditor(text = 'Hello world. This is a test.') {
  const listeners = new Map<string, Set<() => void>>();
  return {
    getText: vi.fn(() => text),
    on: vi.fn((event: string, fn: () => void) => {
      if (!listeners.has(event)) listeners.set(event, new Set());
      listeners.get(event)!.add(fn);
    }),
    off: vi.fn((event: string, fn: () => void) => {
      listeners.get(event)?.delete(fn);
    }),
    _fire: (event: string) => {
      listeners.get(event)?.forEach(fn => fn());
    },
  } as any;
}

describe('useTtsPrewarmer', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers();

    // Reset mock cache size
    (sentenceAudioCache as any).size = 0;

    // Default: all sentences are uncached
    mockFindUncached.mockResolvedValue([
      { index: 0, text: 'Hello world', hash: 'hash-0' },
      { index: 1, text: 'This is a test', hash: 'hash-1' },
    ]);

    // Mock AudioContext
    global.AudioContext = vi.fn().mockImplementation(() => ({
      decodeAudioData: vi.fn(() =>
        Promise.resolve({
          sampleRate: 44100,
          numberOfChannels: 1,
          length: 100,
          getChannelData: vi.fn(() => new Float32Array(100)),
        }),
      ),
      close: vi.fn(),
    })) as any;

    // Mock fetch for audio URLs
    global.fetch = vi.fn(() =>
      Promise.resolve({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      } as Response),
    ) as any;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does NOT fire when TTS has never been used', async () => {
    const editor = makeEditor();

    renderHook(() => useTtsPrewarmer(editor));

    // Simulate editor update
    editor._fire('update');

    // Advance past idle timer
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(api.textToSpeechBatch).not.toHaveBeenCalled();
  });

  it('fires after dyslex-tts-used event', async () => {
    const editor = makeEditor();

    (api.textToSpeechBatch as any).mockResolvedValue({
      data: { results: [] },
    });

    renderHook(() => useTtsPrewarmer(editor));

    // Activate via custom event
    act(() => {
      document.dispatchEvent(new Event('dyslex-tts-used'));
    });

    // Simulate edit + idle
    editor._fire('update');

    await act(async () => {
      vi.advanceTimersByTime(2500);
      await vi.runAllTimersAsync();
    });

    expect(api.textToSpeechBatch).toHaveBeenCalled();
  });

  it('activates when cache already has entries', async () => {
    (sentenceAudioCache as any).size = 3;

    const editor = makeEditor();

    (api.textToSpeechBatch as any).mockResolvedValue({
      data: { results: [] },
    });

    renderHook(() => useTtsPrewarmer(editor));

    editor._fire('update');

    await act(async () => {
      vi.advanceTimersByTime(2500);
      await vi.runAllTimersAsync();
    });

    expect(api.textToSpeechBatch).toHaveBeenCalled();
  });

  it('only sends uncached sentences to the API', async () => {
    const editor = makeEditor('Cached sentence. New sentence.');

    // Only one sentence is uncached
    mockFindUncached.mockResolvedValue([
      { index: 1, text: 'New sentence', hash: 'hash-1' },
    ]);

    (api.textToSpeechBatch as any).mockResolvedValue({
      data: { results: [] },
    });

    renderHook(() => useTtsPrewarmer(editor));

    act(() => {
      document.dispatchEvent(new Event('dyslex-tts-used'));
    });

    editor._fire('update');

    await act(async () => {
      vi.advanceTimersByTime(2500);
      await vi.runAllTimersAsync();
    });

    // Should have been called with only 1 sentence (the uncached one)
    const call = (api.textToSpeechBatch as any).mock.calls[0];
    expect(call[0]).toHaveLength(1);
    expect(call[0][0].text).toBe('New sentence');
  });

  it('debounces: multiple rapid pauses produce a single API call', async () => {
    const editor = makeEditor();

    (api.textToSpeechBatch as any).mockResolvedValue({
      data: { results: [] },
    });

    renderHook(() => useTtsPrewarmer(editor));

    act(() => {
      document.dispatchEvent(new Event('dyslex-tts-used'));
    });

    // Rapid edits: each resets the idle timer
    for (let i = 0; i < 5; i++) {
      editor._fire('update');
      await act(async () => {
        vi.advanceTimersByTime(500);
      });
    }

    // Now wait for idle
    await act(async () => {
      vi.advanceTimersByTime(2500);
      await vi.runAllTimersAsync();
    });

    expect(api.textToSpeechBatch).toHaveBeenCalledTimes(1);
  });

  it('cleans up on unmount', async () => {
    const editor = makeEditor();

    const { unmount } = renderHook(() => useTtsPrewarmer(editor));

    act(() => {
      document.dispatchEvent(new Event('dyslex-tts-used'));
    });

    editor._fire('update');

    // Unmount before idle fires
    unmount();

    await act(async () => {
      vi.advanceTimersByTime(3000);
      await vi.runAllTimersAsync();
    });

    expect(api.textToSpeechBatch).not.toHaveBeenCalled();
  });

  it('handles null editor gracefully', () => {
    expect(() => {
      renderHook(() => useTtsPrewarmer(null));
    }).not.toThrow();
  });

  it('does not call API when all sentences are cached', async () => {
    const editor = makeEditor();

    // No uncached sentences
    mockFindUncached.mockResolvedValue([]);

    renderHook(() => useTtsPrewarmer(editor));

    act(() => {
      document.dispatchEvent(new Event('dyslex-tts-used'));
    });

    editor._fire('update');

    await act(async () => {
      vi.advanceTimersByTime(2500);
      await vi.runAllTimersAsync();
    });

    expect(api.textToSpeechBatch).not.toHaveBeenCalled();
  });
});
