import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useReadAloud } from '../useReadAloud';
import { api } from '@/services/api';
import { useSettingsStore } from '@/stores/settingsStore';

// Mock dependencies
vi.mock('@/services/api');
vi.mock('@/stores/settingsStore');
vi.mock('@/services/ttsSentenceCache', () => ({
  splitIntoSentences: (text: string) => (text.trim() ? [text] : []),
  hashSentence: async () => 'mock-hash',
  sentenceAudioCache: {
    get: () => undefined,
    set: () => {},
    clear: () => {},
  },
}));

describe('useReadAloud', () => {
  beforeEach(() => {
    vi.resetAllMocks();

    // Mock settings store
    (useSettingsStore as any).mockReturnValue({
      ttsSpeed: 1.0,
      voiceEnabled: true,
    });

    // Mock AudioContext
    global.AudioContext = vi.fn().mockImplementation(() => ({
      createBufferSource: vi.fn(() => ({
        buffer: null,
        playbackRate: { value: 1.0 },
        connect: vi.fn(),
        start: vi.fn(),
        stop: vi.fn(),
        onended: null,
      })),
      decodeAudioData: vi.fn(() =>
        Promise.resolve({
          sampleRate: 44100,
          numberOfChannels: 1,
          length: 100,
          getChannelData: vi.fn(() => new Float32Array(100)),
        }),
      ),
      destination: {},
      currentTime: 0,
      state: 'running',
      close: vi.fn(),
      resume: vi.fn(() => Promise.resolve()),
    })) as any;

    // Mock SpeechSynthesisUtterance
    global.SpeechSynthesisUtterance = vi.fn().mockImplementation((text: string) => ({
      text,
      rate: 1,
      onstart: null,
      onend: null,
      onerror: null,
    })) as any;

    // Mock SpeechSynthesis
    global.speechSynthesis = {
      speak: vi.fn((utterance: any) => {
        utterance.onstart?.();
      }),
      cancel: vi.fn(),
      pause: vi.fn(() => {
        (global as any).speechSynthesis.paused = true;
      }),
      resume: vi.fn(() => {
        (global as any).speechSynthesis.paused = false;
      }),
      paused: false,
    } as any;
  });

  describe('Initialization', () => {
    it('initializes with idle state', () => {
      const { result } = renderHook(() => useReadAloud());

      expect(result.current.state).toBe('idle');
      expect(result.current.isPlaying).toBe(false);
      expect(result.current.isPaused).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe('MagpieTTS Backend', () => {
    it('uses MagpieTTS by default', async () => {
      (api.textToSpeechBatch as any).mockResolvedValue({
        data: {
          results: [{ index: 0, audio_url: 'http://localhost:8000/audio/test.mp3' }],
        },
      });

      global.fetch = vi.fn(() =>
        Promise.resolve({
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
        } as Response)
      ) as any;

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Hello world');
      });

      expect(api.textToSpeechBatch).toHaveBeenCalled();
    });

    it('falls back to browser TTS on MagpieTTS error', async () => {
      (api.textToSpeechBatch as any).mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Hello world');
      });

      expect(speechSynthesis.speak).toHaveBeenCalled();
    });
  });

  describe('Browser TTS Fallback', () => {
    it('uses browser TTS when MagpieTTS fails', async () => {
      (api.textToSpeechBatch as any).mockRejectedValue(new Error('Server error'));

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Test text');
      });

      expect(speechSynthesis.speak).toHaveBeenCalled();
      const utterance = (speechSynthesis.speak as any).mock.calls[0][0];
      expect(utterance.text).toBe('Test text');
    });

    it('respects TTS speed setting', async () => {
      (useSettingsStore as any).mockReturnValue({
        ttsSpeed: 1.5,
        voiceEnabled: true,
      });

      (api.textToSpeechBatch as any).mockRejectedValue(new Error('Fallback'));

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Fast speech');
      });

      const utterance = (speechSynthesis.speak as any).mock.calls[0][0];
      expect(utterance.rate).toBe(1.5);
    });
  });

  describe('Playback Controls', () => {
    it('pauses playback', async () => {
      const { result } = renderHook(() => useReadAloud());

      // Simulate playing state
      await act(async () => {
        result.current.speak('Test');
      });

      act(() => {
        result.current.pause();
      });

      expect(result.current.isPaused).toBe(true);
    });

    it('resumes playback', async () => {
      const { result } = renderHook(() => useReadAloud());

      // Get to playing state via browser TTS fallback
      await act(async () => {
        await result.current.speak('Test');
      });

      // Pause to reach paused state
      act(() => {
        result.current.pause();
      });

      // Now resume
      act(() => {
        result.current.resume();
      });

      expect(speechSynthesis.resume).toHaveBeenCalled();
    });

    it('stops playback', async () => {
      const { result } = renderHook(() => useReadAloud());

      act(() => {
        result.current.stop();
      });

      expect(speechSynthesis.cancel).toHaveBeenCalled();
      expect(result.current.state).toBe('idle');
    });
  });

  describe('Settings Integration', () => {
    it('does not speak when voice disabled', async () => {
      (useSettingsStore as any).mockReturnValue({
        ttsSpeed: 1.0,
        voiceEnabled: false,
      });

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Should not speak');
      });

      expect(api.textToSpeechBatch).not.toHaveBeenCalled();
      expect(speechSynthesis.speak).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('sets error when TTS not supported', async () => {
      delete (global as any).speechSynthesis;
      (api.textToSpeechBatch as any).mockRejectedValue(new Error('Fallback'));

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Test');
      });

      expect(result.current.error).toBeTruthy();
    });
  });
});
