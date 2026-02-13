import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useVoiceInput } from '../useVoiceInput';

let mockRecognition: any;

beforeEach(() => {
  mockRecognition = {
    start: vi.fn(),
    stop: vi.fn(),
    lang: '',
    continuous: false,
    interimResults: false,
    onresult: null as any,
    onerror: null as any,
    onend: null as any,
  };

  window.SpeechRecognition = vi.fn(() => mockRecognition) as any;
  delete (window as any).webkitSpeechRecognition;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useVoiceInput', () => {
  describe('Initialization', () => {
    it('initializes with idle state', () => {
      const { result } = renderHook(() => useVoiceInput());

      expect(result.current.isListening).toBe(false);
      expect(result.current.transcript).toBe('');
      expect(result.current.interimText).toBe('');
    });

    it('detects browser support when SpeechRecognition exists', () => {
      const { result } = renderHook(() => useVoiceInput());
      expect(result.current.isSupported).toBe(true);
    });

    it('detects no browser support when SpeechRecognition absent', () => {
      delete (window as any).SpeechRecognition;
      delete (window as any).webkitSpeechRecognition;

      const { result } = renderHook(() => useVoiceInput());
      expect(result.current.isSupported).toBe(false);
    });

    it('detects browser support via webkitSpeechRecognition', () => {
      delete (window as any).SpeechRecognition;
      (window as any).webkitSpeechRecognition = vi.fn(() => mockRecognition);

      const { result } = renderHook(() => useVoiceInput());
      expect(result.current.isSupported).toBe(true);
    });

    it('configures recognition with provided language', () => {
      renderHook(() => useVoiceInput({ language: 'fr-FR' }));
      expect(mockRecognition.lang).toBe('fr-FR');
    });

    it('sets continuous and interimResults', () => {
      renderHook(() => useVoiceInput({ continuous: true }));
      expect(mockRecognition.continuous).toBe(true);
      expect(mockRecognition.interimResults).toBe(true);
    });
  });

  describe('Start/Stop Listening', () => {
    it('start listening calls recognition.start', () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      expect(mockRecognition.start).toHaveBeenCalled();
      expect(result.current.isListening).toBe(true);
    });

    it('stop listening calls recognition.stop', () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        result.current.stopListening();
      });

      expect(mockRecognition.stop).toHaveBeenCalled();
      expect(result.current.isListening).toBe(false);
    });

    it('start does nothing when already listening', () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });
      mockRecognition.start.mockClear();

      act(() => {
        result.current.startListening();
      });

      expect(mockRecognition.start).not.toHaveBeenCalled();
    });
  });

  describe('Result Events', () => {
    it('final result updates transcript and calls onResult', () => {
      const onResult = vi.fn();
      const { result } = renderHook(() => useVoiceInput({ onResult }));

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onresult({
          results: [
            { 0: { transcript: 'hello world' }, isFinal: true, length: 1 },
          ],
          length: 1,
        });
      });

      expect(result.current.transcript).toContain('Hello world.');
      expect(onResult).toHaveBeenCalledWith('Hello world.');
    });

    it('interim result updates interimText', () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onresult({
          results: [
            { 0: { transcript: 'hel' }, isFinal: false, length: 1 },
          ],
          length: 1,
        });
      });

      expect(result.current.interimText).toBe('Hel');
    });
  });

  describe('Error Handling', () => {
    it('no-speech error is ignored', () => {
      const onError = vi.fn();
      const { result } = renderHook(() => useVoiceInput({ onError }));

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onerror({ error: 'no-speech' });
      });

      expect(onError).not.toHaveBeenCalled();
      // isListening stays true (not disrupted)
    });

    it('aborted error is ignored', () => {
      const onError = vi.fn();
      renderHook(() => useVoiceInput({ onError }));

      act(() => {
        mockRecognition.onerror({ error: 'aborted' });
      });

      expect(onError).not.toHaveBeenCalled();
    });

    it('real error fires onError callback', () => {
      const onError = vi.fn();
      const { result } = renderHook(() => useVoiceInput({ onError }));

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onerror({ error: 'network' });
      });

      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
      expect(onError.mock.calls[0][0].message).toContain('network');
      expect(result.current.isListening).toBe(false);
    });
  });

  describe('Continuous Mode', () => {
    it('auto-restarts on end when continuous and not stopping', () => {
      const { result } = renderHook(() => useVoiceInput({ continuous: true }));

      act(() => {
        result.current.startListening();
      });
      mockRecognition.start.mockClear();

      // Simulate the recognition ending (browser auto-stop on silence)
      act(() => {
        mockRecognition.onend();
      });

      // Should have called start() again for auto-restart
      expect(mockRecognition.start).toHaveBeenCalled();
    });

    it('does not auto-restart after explicit stop', () => {
      const { result } = renderHook(() => useVoiceInput({ continuous: true }));

      act(() => {
        result.current.startListening();
      });

      act(() => {
        result.current.stopListening();
      });
      mockRecognition.start.mockClear();

      act(() => {
        mockRecognition.onend();
      });

      expect(mockRecognition.start).not.toHaveBeenCalled();
      expect(result.current.isListening).toBe(false);
    });
  });

  describe('Reset Transcript', () => {
    it('clears transcript and interimText', () => {
      const { result } = renderHook(() => useVoiceInput());

      act(() => {
        result.current.startListening();
      });

      // Simulate a final result
      act(() => {
        mockRecognition.onresult({
          results: [
            { 0: { transcript: 'some text' }, isFinal: true, length: 1 },
          ],
          length: 1,
        });
      });

      expect(result.current.transcript).toContain('Some text.');

      act(() => {
        result.current.resetTranscript();
      });

      expect(result.current.transcript).toBe('');
      expect(result.current.interimText).toBe('');
    });
  });
});
