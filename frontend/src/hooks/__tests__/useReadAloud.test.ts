import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { renderHook, act } from '@testing-library/react';
import { useReadAloud } from '../useReadAloud';
import { api } from '@/services/api';
import { useSettingsStore } from '@/stores/settingsStore';

// Mock dependencies
jest.mock('@/services/api');
jest.mock('@/stores/settingsStore');

describe('useReadAloud', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Mock settings store
    (useSettingsStore as jest.Mock).mockReturnValue({
      ttsSpeed: 1.0,
      voiceEnabled: true,
    });

    // Mock AudioContext
    global.AudioContext = jest.fn().mockImplementation(() => ({
      createBufferSource: jest.fn(() => ({
        buffer: null,
        playbackRate: { value: 1.0 },
        connect: jest.fn(),
        start: jest.fn(),
        stop: jest.fn(),
        onended: null,
      })),
      decodeAudioData: jest.fn(() => Promise.resolve({})),
      destination: {},
      currentTime: 0,
      close: jest.fn(),
    })) as any;

    // Mock SpeechSynthesis
    global.speechSynthesis = {
      speak: jest.fn(),
      cancel: jest.fn(),
      pause: jest.fn(),
      resume: jest.fn(),
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
      const mockAudioUrl = 'http://localhost:8000/audio/test.mp3';
      (api.textToSpeech as jest.Mock).mockResolvedValue({
        data: { audio_url: mockAudioUrl },
      });

      global.fetch = jest.fn(() =>
        Promise.resolve({
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
        } as Response)
      ) as jest.Mock;

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Hello world');
      });

      expect(api.textToSpeech).toHaveBeenCalledWith('Hello world', undefined);
    });

    it('falls back to browser TTS on MagpieTTS error', async () => {
      (api.textToSpeech as jest.Mock).mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Hello world');
      });

      expect(speechSynthesis.speak).toHaveBeenCalled();
    });
  });

  describe('Browser TTS Fallback', () => {
    it('uses browser TTS when MagpieTTS fails', async () => {
      (api.textToSpeech as jest.Mock).mockRejectedValue(new Error('Server error'));

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Test text');
      });

      expect(speechSynthesis.speak).toHaveBeenCalled();
      const utterance = (speechSynthesis.speak as jest.Mock).mock.calls[0][0];
      expect(utterance.text).toBe('Test text');
    });

    it('respects TTS speed setting', async () => {
      (useSettingsStore as jest.Mock).mockReturnValue({
        ttsSpeed: 1.5,
        voiceEnabled: true,
      });

      (api.textToSpeech as jest.Mock).mockRejectedValue(new Error('Fallback'));

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Fast speech');
      });

      const utterance = (speechSynthesis.speak as jest.Mock).mock.calls[0][0];
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
      (speechSynthesis as any).paused = true;

      const { result } = renderHook(() => useReadAloud());

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
      (useSettingsStore as jest.Mock).mockReturnValue({
        ttsSpeed: 1.0,
        voiceEnabled: false,
      });

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Should not speak');
      });

      expect(api.textToSpeech).not.toHaveBeenCalled();
      expect(speechSynthesis.speak).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('sets error when TTS not supported', async () => {
      delete (global as any).speechSynthesis;
      (api.textToSpeech as jest.Mock).mockRejectedValue(new Error('Fallback'));

      const { result } = renderHook(() => useReadAloud());

      await act(async () => {
        await result.current.speak('Test');
      });

      expect(result.current.error).toBeTruthy();
    });
  });
});
