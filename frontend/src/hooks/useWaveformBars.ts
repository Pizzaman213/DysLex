/**
 * Hook that reads frequency data from an AnalyserNode and returns
 * normalized bar heights for waveform visualization.
 *
 * Uses requestAnimationFrame for smooth 60fps updates and exponential
 * smoothing to avoid jittery bars.
 */

import { useEffect, useRef, useState } from 'react';

const DEFAULT_BAR_COUNT = 7;
const SMOOTH_UP = 0.45;   // rise: 55% new data — responsive
const SMOOTH_DOWN = 0.82; // fall: 18% new data — slow, fluid decay
const IDLE_HEIGHT = 0.15;

export function useWaveformBars(
  analyserNode: AnalyserNode | null,
  barCount: number = DEFAULT_BAR_COUNT,
  /**
   * When true, compute overall voice energy and distribute it across all bars
   * with a flowing sine wave — every bar reacts to voice. Use for radial visualizers.
   * When false (default), each bar maps to a slice of the frequency spectrum.
   */
  radial: boolean = false,
): number[] {
  const [bars, setBars] = useState<number[]>(() =>
    Array(barCount).fill(IDLE_HEIGHT),
  );
  const prevBarsRef = useRef<number[]>(Array(barCount).fill(IDLE_HEIGHT));
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!analyserNode) {
      prevBarsRef.current = Array(barCount).fill(IDLE_HEIGHT);
      setBars(Array(barCount).fill(IDLE_HEIGHT));
      return;
    }

    const bufferLength = analyserNode.frequencyBinCount; // 128 for fftSize=256
    const dataArray = new Uint8Array(bufferLength);
    const binsPerBar = Math.floor(bufferLength / barCount);

    function tick() {
      analyserNode!.getByteFrequencyData(dataArray);

      const next: number[] = [];

      if (radial) {
        // Radial mode: compute energy from speech-relevant bins only (first ~30),
        // then distribute across all bars with a flowing sine wave.
        const speechBins = Math.min(30, bufferLength);
        let totalEnergy = 0;
        let peakBin = 0;
        for (let j = 0; j < speechBins; j++) {
          totalEnergy += dataArray[j];
          if (dataArray[j] > peakBin) peakBin = dataArray[j];
        }
        // Blend RMS-style average with peak for punchy response
        const avg = totalEnergy / (speechBins * 255);
        const peak = peakBin / 255;
        const energy = Math.min(avg * 1.8 + peak * 0.4, 1);

        const now = performance.now() / 600; // slow rotation for fluid flow
        for (let i = 0; i < barCount; i++) {
          const phase = now + (i * Math.PI * 2) / barCount;
          const wave = 0.55 + 0.45 * Math.sin(phase);
          const raw = energy * wave;

          const prev = prevBarsRef.current[i];
          const smoothing = raw > prev ? SMOOTH_UP : SMOOTH_DOWN;
          const smoothed = smoothing * prev + (1 - smoothing) * raw;
          next.push(Math.max(smoothed, IDLE_HEIGHT));
        }
      } else {
        // Linear mode: each bar maps to a frequency bin slice
        for (let i = 0; i < barCount; i++) {
          const start = i * binsPerBar;
          const end = start + binsPerBar;
          let sum = 0;
          for (let j = start; j < end; j++) {
            sum += dataArray[j];
          }
          const raw = sum / (binsPerBar * 255);
          const prev = prevBarsRef.current[i];
          const smoothing = raw > prev ? SMOOTH_UP : SMOOTH_DOWN;
          const smoothed = smoothing * prev + (1 - smoothing) * raw;
          next.push(Math.max(smoothed, IDLE_HEIGHT));
        }
      }

      prevBarsRef.current = next;
      setBars(next);
      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [analyserNode, barCount, radial]);

  return bars;
}
