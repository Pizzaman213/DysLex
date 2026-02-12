/**
 * Hook that drives a radial waveform visualizer by writing directly to the DOM.
 *
 * Each bar is anchored at the wrapper center (bottom: 50%), rotated to its angle.
 * The hook adjusts each bar's height — the mic button covers the inner portion,
 * so only the part extending beyond the mic edge is visible.
 */

import { useEffect, useRef } from 'react';

const BAR_COUNT = 16;
const ANGLE_STEP = 360 / BAR_COUNT; // 22.5°
const SMOOTH_UP = 0.45;
const SMOOTH_DOWN = 0.82;
const IDLE_HEIGHT = 0.15;
const MIC_RADIUS = 48;    // half of 96px mic button
const GAP = 6;             // space between mic edge and visible bar start
const BAR_MAX = 40;        // max dynamic bar length in px

export function useRadialWaveform(
  waveRef: React.RefObject<HTMLDivElement | null>,
  analyserNode: AnalyserNode | null,
): void {
  const prevBarsRef = useRef<number[]>(Array(BAR_COUNT).fill(IDLE_HEIGHT));
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const container = waveRef.current;
    if (!container) return;

    const barEls = container.querySelectorAll<HTMLElement>('.radial-bar');
    if (barEls.length !== BAR_COUNT) return;

    // Set initial rotation + idle height for each bar
    for (let i = 0; i < BAR_COUNT; i++) {
      const angle = i * ANGLE_STEP;
      barEls[i].style.transform = `rotate(${angle}deg)`;
      barEls[i].style.height = `${MIC_RADIUS + GAP + BAR_MAX * IDLE_HEIGHT}px`;
    }

    if (!analyserNode) {
      prevBarsRef.current = Array(BAR_COUNT).fill(IDLE_HEIGHT);
      return;
    }

    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function tick() {
      analyserNode!.getByteFrequencyData(dataArray);

      // Energy from speech-relevant bins (first ~30)
      const speechBins = Math.min(30, bufferLength);
      let totalEnergy = 0;
      let peakBin = 0;
      for (let j = 0; j < speechBins; j++) {
        totalEnergy += dataArray[j];
        if (dataArray[j] > peakBin) peakBin = dataArray[j];
      }
      const avg = totalEnergy / (speechBins * 255);
      const peak = peakBin / 255;
      const energy = Math.min(avg * 1.8 + peak * 0.4, 1);

      const now = performance.now() / 800;
      for (let i = 0; i < BAR_COUNT; i++) {
        const wobble = 1 + 0.12 * Math.sin(now + i * 1.3);
        const raw = energy * wobble;

        const prev = prevBarsRef.current[i];
        const smoothing = raw > prev ? SMOOTH_UP : SMOOTH_DOWN;
        const smoothed = smoothing * prev + (1 - smoothing) * raw;
        const value = Math.max(smoothed, IDLE_HEIGHT);
        prevBarsRef.current[i] = value;

        barEls[i].style.height = `${MIC_RADIUS + GAP + BAR_MAX * value}px`;
      }

      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [waveRef, analyserNode]);
}
