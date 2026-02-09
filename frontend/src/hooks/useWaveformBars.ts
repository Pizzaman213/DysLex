/**
 * Hook that reads frequency data from an AnalyserNode and returns
 * normalized bar heights for waveform visualization.
 *
 * Uses requestAnimationFrame for smooth 60fps updates and exponential
 * smoothing to avoid jittery bars.
 */

import { useEffect, useRef, useState } from 'react';

const DEFAULT_BAR_COUNT = 7;
const SMOOTHING = 0.6; // 60% previous, 40% new
const IDLE_HEIGHT = 0.15;

export function useWaveformBars(
  analyserNode: AnalyserNode | null,
  barCount: number = DEFAULT_BAR_COUNT,
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
      for (let i = 0; i < barCount; i++) {
        const start = i * binsPerBar;
        const end = start + binsPerBar;
        let sum = 0;
        for (let j = start; j < end; j++) {
          sum += dataArray[j];
        }
        // Normalize 0-255 → 0-1
        const raw = sum / (binsPerBar * 255);
        // Exponential smoothing
        const smoothed =
          SMOOTHING * prevBarsRef.current[i] + (1 - SMOOTHING) * raw;
        // Ensure minimum height
        next.push(Math.max(smoothed, IDLE_HEIGHT));
      }

      prevBarsRef.current = next;
      setBars(next);
      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [analyserNode, barCount]);

  return bars;
}
