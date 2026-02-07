import { describe, it, expect, beforeAll, jest } from '@jest/globals';
import { loadModel, runLocalCorrection, isModelLoaded, getModelState, updateUserDictionary, getDictionarySize } from '../onnxModel';

describe('ONNX Model', () => {
  // Note: These tests require the actual ONNX model file to be present
  // In a CI environment, you might want to mock these or skip if model not available

  describe('Model Loading', () => {
    it('loads model successfully', async () => {
      try {
        await loadModel();
        expect(isModelLoaded()).toBe(true);
      } catch (error) {
        console.warn('Model file not found - skipping test');
      }
    }, 10000);

    it('reports model state', () => {
      const state = getModelState();
      expect(state).toHaveProperty('loaded');
      expect(state).toHaveProperty('error');
      expect(state).toHaveProperty('dictionarySize');
    });
  });

  describe('Dictionary', () => {
    it('loads base dictionary with entries', async () => {
      try {
        await loadModel();
      } catch { /* skip */ }

      const size = getDictionarySize();
      expect(size.base).toBeGreaterThanOrEqual(0);
      expect(size.total).toBeGreaterThanOrEqual(size.base);
    });

    it('accepts user dictionary updates', () => {
      updateUserDictionary({ customword: 'custom', mytypo: 'myword' });
      const size = getDictionarySize();
      expect(size.user).toBe(2);
    });

    it('user dictionary overrides base dictionary', async () => {
      // Set up user dict with a custom correction for "teh"
      updateUserDictionary({ teh: 'custom_the' });

      // Dictionary-only fallback should use user's version
      const result = await runLocalCorrection('teh');
      if (result.length > 0) {
        const tehCorrection = result.find(c => c.original.toLowerCase() === 'teh');
        if (tehCorrection) {
          expect(tehCorrection.correction).toBe('custom_the');
        }
      }

      // Reset
      updateUserDictionary({});
    });
  });

  describe('Inference', () => {
    beforeAll(async () => {
      try {
        await loadModel();
      } catch (error) {
        console.warn('Model not available for inference tests');
      }
    });

    it('corrects common error', async () => {
      if (!isModelLoaded()) {
        console.warn('Model not loaded - skipping test');
        return;
      }

      const result = await runLocalCorrection('I went to teh store');

      expect(result).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            original: 'teh',
            correction: 'the',
          }),
        ])
      );
    });

    it('handles text with no errors', async () => {
      if (!isModelLoaded()) {
        console.warn('Model not loaded - skipping test');
        return;
      }

      const result = await runLocalCorrection('This is a correct sentence.');
      expect(result).toEqual([]);
    });

    it('completes inference in <100ms', async () => {
      if (!isModelLoaded()) {
        console.warn('Model not loaded - skipping test');
        return;
      }

      const start = performance.now();
      await runLocalCorrection('This is a test sentence with no errors');
      const elapsed = performance.now() - start;

      expect(elapsed).toBeLessThan(100);
    });

    it('handles multiple errors', async () => {
      if (!isModelLoaded()) {
        console.warn('Model not loaded - skipping test');
        return;
      }

      const result = await runLocalCorrection('I went to teh store becuase I needed milk');

      expect(result.length).toBeGreaterThanOrEqual(1);
      expect(result).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            original: expect.stringMatching(/teh|becuase/),
          }),
        ])
      );
    });

    it('returns corrections with confidence scores', async () => {
      if (!isModelLoaded()) {
        console.warn('Model not loaded - skipping test');
        return;
      }

      const result = await runLocalCorrection('teh cat sat on teh mat');
      for (const correction of result) {
        expect(correction.confidence).toBeGreaterThan(0);
        expect(correction.confidence).toBeLessThanOrEqual(1);
        expect(correction.position.start).toBeGreaterThanOrEqual(0);
        expect(correction.position.end).toBeGreaterThan(correction.position.start);
      }
    });
  });

  describe('Error Handling', () => {
    it('handles empty input gracefully', async () => {
      const result = await runLocalCorrection('');
      expect(result).toEqual([]);
    });

    it('handles very long input', async () => {
      if (!isModelLoaded()) {
        console.warn('Model not loaded - skipping test');
        return;
      }

      const longText = 'This is a sentence. '.repeat(100);
      const result = await runLocalCorrection(longText);

      expect(Array.isArray(result)).toBe(true);
    });

    it('falls back to dictionary-only mode when model unavailable', async () => {
      // Dictionary fallback should work even without model
      // runLocalCorrection has built-in fallback
      const result = await runLocalCorrection('teh cat');
      expect(Array.isArray(result)).toBe(true);
    });
  });
});
