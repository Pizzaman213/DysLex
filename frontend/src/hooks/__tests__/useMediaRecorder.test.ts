import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMediaRecorder } from '../useMediaRecorder';

let mockStream: any;
let mockRecorder: any;
let mockAudioCtx: any;
let mockAnalyser: any;
let mockSource: any;

beforeEach(() => {
  // Mock MediaStream
  mockStream = {
    getTracks: vi.fn(() => [{ stop: vi.fn() }]),
  };

  // Mock MediaRecorder instance
  mockRecorder = {
    start: vi.fn(),
    stop: vi.fn(),
    state: 'inactive' as string,
    mimeType: 'audio/webm;codecs=opus',
    stream: mockStream,
    ondataavailable: null as any,
    onstop: null as any,
  };

  // Mock AnalyserNode
  mockAnalyser = {
    fftSize: 0,
    connect: vi.fn(),
  };

  // Mock MediaStreamSource
  mockSource = {
    connect: vi.fn(),
  };

  // Mock AudioContext
  mockAudioCtx = {
    createMediaStreamSource: vi.fn(() => mockSource),
    createAnalyser: vi.fn(() => mockAnalyser),
    close: vi.fn(),
  };

  // Wire up navigator.mediaDevices
  Object.defineProperty(navigator, 'mediaDevices', {
    value: {
      getUserMedia: vi.fn(() => Promise.resolve(mockStream)),
    },
    writable: true,
    configurable: true,
  });

  // Wire up MediaRecorder constructor
  global.MediaRecorder = vi.fn().mockImplementation(() => {
    // When start() is called, change state to 'recording'
    mockRecorder.start = vi.fn(() => {
      mockRecorder.state = 'recording';
    });
    mockRecorder.stop = vi.fn(() => {
      mockRecorder.state = 'inactive';
      // Trigger onstop asynchronously
      setTimeout(() => mockRecorder.onstop?.(), 0);
    });
    return mockRecorder;
  }) as any;
  (global.MediaRecorder as any).isTypeSupported = vi.fn(
    (type: string) => type === 'audio/webm;codecs=opus'
  );

  // Wire up AudioContext
  global.AudioContext = vi.fn(() => mockAudioCtx) as any;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useMediaRecorder', () => {
  describe('Initialization', () => {
    it('not recording initially', () => {
      const { result } = renderHook(() => useMediaRecorder());

      expect(result.current.isRecording).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe('Start Recording', () => {
    it('requests microphone access', async () => {
      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
    });

    it('creates AudioContext and AnalyserNode', async () => {
      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(AudioContext).toHaveBeenCalled();
      expect(mockAudioCtx.createMediaStreamSource).toHaveBeenCalledWith(mockStream);
      expect(mockAudioCtx.createAnalyser).toHaveBeenCalled();
      expect(mockSource.connect).toHaveBeenCalledWith(mockAnalyser);
    });

    it('sets isRecording to true', async () => {
      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(result.current.isRecording).toBe(true);
    });

    it('creates MediaRecorder with preferred MIME type', async () => {
      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(global.MediaRecorder).toHaveBeenCalledWith(
        mockStream,
        expect.objectContaining({ mimeType: 'audio/webm;codecs=opus' })
      );
    });
  });

  describe('Stop Recording', () => {
    it('returns blob after stopping', async () => {
      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      // Simulate data available
      act(() => {
        mockRecorder.ondataavailable({ data: new Blob(['audio-data'], { type: 'audio/webm' }) });
      });

      let blob: Blob | null = null;
      await act(async () => {
        blob = await result.current.stopRecording();
      });

      expect(blob).toBeInstanceOf(Blob);
      expect(result.current.isRecording).toBe(false);
    });

    it('returns null when stopping inactive recorder', async () => {
      const { result } = renderHook(() => useMediaRecorder());

      // Don't start recording — stop immediately
      let blob: Blob | null = new Blob(); // non-null initial
      await act(async () => {
        blob = await result.current.stopRecording();
      });

      expect(blob).toBeNull();
      expect(result.current.isRecording).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('sets error when mic permission denied', async () => {
      (navigator.mediaDevices.getUserMedia as any).mockRejectedValueOnce(
        new Error('Permission denied')
      );

      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(result.current.error).toBe('Permission denied');
      expect(result.current.isRecording).toBe(false);
    });

    it('sets error with fallback message for non-Error throws', async () => {
      (navigator.mediaDevices.getUserMedia as any).mockRejectedValueOnce('unknown');

      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(result.current.error).toBe('Failed to start recording');
    });
  });

  describe('Cleanup', () => {
    it('stops tracks and closes AudioContext on stop', async () => {
      const mockTrack = { stop: vi.fn() };
      mockStream.getTracks = vi.fn(() => [mockTrack]);

      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      await act(async () => {
        await result.current.stopRecording();
      });

      expect(mockTrack.stop).toHaveBeenCalled();
      expect(mockAudioCtx.close).toHaveBeenCalled();
    });
  });

  describe('MIME Type Selection', () => {
    it('prefers opus codec', async () => {
      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      // The MediaRecorder constructor should have been called with opus mime
      expect(global.MediaRecorder).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ mimeType: 'audio/webm;codecs=opus' })
      );
    });

    it('falls back when opus not supported', async () => {
      (global.MediaRecorder as any).isTypeSupported = vi.fn(
        (type: string) => type === 'audio/webm'
      );

      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(global.MediaRecorder).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ mimeType: 'audio/webm' })
      );
    });

    it('uses empty string when no types supported', async () => {
      (global.MediaRecorder as any).isTypeSupported = vi.fn(() => false);

      const { result } = renderHook(() => useMediaRecorder());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(global.MediaRecorder).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ mimeType: '' })
      );
    });
  });
});
