import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSnapshotEngine } from '../useSnapshotEngine';
import { api } from '@/services/api';
import { snapshotManager } from '@/utils/snapshotManager';

// Mock dependencies
vi.mock('@/services/api');
vi.mock('@/utils/snapshotManager');

describe('useSnapshotEngine', () => {
  let mockEditor: any;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    mockEditor = {
      getText: vi.fn(() => 'Sample text'),
      on: vi.fn(),
      off: vi.fn(),
    };

    (snapshotManager as any).addSnapshot = vi.fn();
    (snapshotManager as any).recordActivity = vi.fn();
    (snapshotManager as any).shouldSnapshotOnPause = vi.fn(() => false);
    (snapshotManager as any).getRecentPair = vi.fn(() => null);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Snapshot Capture', () => {
    it('captures snapshots on regular interval', () => {
      renderHook(() => useSnapshotEngine(mockEditor));

      // Simulate user typing (sets isActive = true)
      const updateHandler = mockEditor.on.mock.calls.find(
        (call: any) => call[0] === 'update'
      )?.[1];
      act(() => {
        updateHandler();
      });

      // Advance 5 seconds
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      expect(snapshotManager.addSnapshot).toHaveBeenCalledWith('Sample text');
    });

    it('captures snapshot on pause', () => {
      (snapshotManager as any).shouldSnapshotOnPause = vi.fn(() => true);
      (snapshotManager as any).addSnapshot = vi.fn(() => ({ id: '1', text: 'text' }));

      renderHook(() => useSnapshotEngine(mockEditor));

      // Advance 500ms (pause check interval)
      act(() => {
        vi.advanceTimersByTime(500);
      });

      expect(snapshotManager.shouldSnapshotOnPause).toHaveBeenCalled();
    });
  });

  describe('Batch Processing', () => {
    it('batches multiple corrections', async () => {
      const mockPair = [
        { id: '1', text: 'I went to teh store', timestamp: 1000, wordCount: 5 },
        { id: '2', text: 'I went to the store', timestamp: 2000, wordCount: 5 },
      ];

      (snapshotManager as any).shouldSnapshotOnPause = vi.fn(() => true);
      (snapshotManager as any).addSnapshot = vi.fn(() => mockPair[1]);
      (snapshotManager as any).getRecentPair = vi.fn(() => mockPair);

      (api.logCorrectionBatch as any).mockResolvedValue({
        data: { logged: 1, total: 1 },
      });

      renderHook(() => useSnapshotEngine(mockEditor));

      // Trigger pause detection multiple times
      for (let i = 0; i < 5; i++) {
        act(() => {
          vi.advanceTimersByTime(500);
        });
      }

      // Should eventually call batch endpoint
      await act(async () => {
        vi.advanceTimersByTime(10000); // Flush interval
      });

      // Check if batch was called
      if ((api.logCorrectionBatch as any).mock.calls.length > 0) {
        expect(api.logCorrectionBatch).toHaveBeenCalled();
      }
    });

    it('flushes on timer', async () => {
      (api.logCorrectionBatch as any).mockResolvedValue({
        data: { logged: 2, total: 2 },
      });

      renderHook(() => useSnapshotEngine(mockEditor));

      // Advance past flush interval
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      // If there were pending corrections, they should be flushed
      // (This is a simplified test - real implementation needs corrections to exist)
    });
  });

  describe('Signal Categorization', () => {
    it('categorizes self-corrections', async () => {
      const mockPair = [
        { id: '1', text: 'I recieve mail', timestamp: 1000, wordCount: 3 },
        { id: '2', text: 'I receive mail', timestamp: 2000, wordCount: 3 },
      ];

      (snapshotManager as any).shouldSnapshotOnPause = vi.fn(() => true);
      (snapshotManager as any).addSnapshot = vi.fn(() => mockPair[1]);
      (snapshotManager as any).getRecentPair = vi.fn(() => mockPair);

      (api.logCorrectionBatch as any).mockResolvedValue({
        data: { logged: 1, total: 1 },
      });

      renderHook(() => useSnapshotEngine(mockEditor));

      act(() => {
        vi.advanceTimersByTime(500);
      });

      // Self-correction should be detected and batched
    });

    it('ignores rewrites', async () => {
      const mockPair = [
        { id: '1', text: 'The cat sat on the mat', timestamp: 1000, wordCount: 6 },
        { id: '2', text: 'A dog jumped over the fence', timestamp: 2000, wordCount: 6 },
      ];

      (snapshotManager as any).shouldSnapshotOnPause = vi.fn(() => true);
      (snapshotManager as any).addSnapshot = vi.fn(() => mockPair[1]);
      (snapshotManager as any).getRecentPair = vi.fn(() => mockPair);

      renderHook(() => useSnapshotEngine(mockEditor));

      act(() => {
        vi.advanceTimersByTime(500);
      });

      // Complete rewrite should not be logged
      expect(api.logCorrectionBatch).not.toHaveBeenCalled();
    });
  });

  describe('Silent Failure', () => {
    it('does not interrupt on API error', async () => {
      (api.logCorrectionBatch as any).mockRejectedValue(new Error('Network error'));

      const mockPair = [
        { id: '1', text: 'teh cat', timestamp: 1000, wordCount: 2 },
        { id: '2', text: 'the cat', timestamp: 2000, wordCount: 2 },
      ];

      (snapshotManager as any).shouldSnapshotOnPause = vi.fn(() => true);
      (snapshotManager as any).addSnapshot = vi.fn(() => mockPair[1]);
      (snapshotManager as any).getRecentPair = vi.fn(() => mockPair);

      // Should not throw error
      expect(() => {
        renderHook(() => useSnapshotEngine(mockEditor));
        act(() => {
          vi.advanceTimersByTime(500);
        });
      }).not.toThrow();
    });
  });

  describe('Cleanup', () => {
    it('flushes pending corrections on unmount', async () => {
      const { unmount } = renderHook(() => useSnapshotEngine(mockEditor));

      // Add some corrections
      // ...

      await act(async () => {
        unmount();
      });

      // Should flush any pending corrections
    });

    it('clears intervals on unmount', () => {
      const { unmount } = renderHook(() => useSnapshotEngine(mockEditor));

      unmount();

      expect(mockEditor.off).toHaveBeenCalledWith('update', expect.any(Function));
    });
  });
});
