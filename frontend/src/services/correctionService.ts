import { api } from './api';
import { runLocalCorrection } from './onnxModel';
import type { LocalCorrection } from './onnxModel';

export interface Correction {
  original: string;
  suggested: string;
  type: 'spelling' | 'grammar' | 'confusion' | 'phonetic' | 'homophone' | 'clarity' | 'style';
  start: number;
  end: number;
  confidence: number;
  explanation?: string;
}

/**
 * Map a LocalCorrection from the ONNX model to the UI Correction format.
 */
function mapLocalCorrection(lc: LocalCorrection): Correction {
  return {
    original: lc.original,
    suggested: lc.correction,
    type: 'spelling',
    start: lc.position.start,
    end: lc.position.end,
    confidence: lc.confidence,
  };
}

export async function getCorrections(text: string): Promise<Correction[]> {
  if (!text.trim()) return [];

  // Tier 1: Quick local ONNX corrections (personalized dictionary + model)
  const localCorrections = await runLocalCorrection(text);

  if (localCorrections.length > 0) {
    return localCorrections.map(mapLocalCorrection);
  }

  // Tier 2: Fall back to cloud API for deeper analysis
  try {
    const response = await api.getCorrections(text);
    return response.data.corrections.map((c: any) => ({
      original: c.original || '',
      suggested: c.correction || c.suggested || '',
      type: c.error_type || c.type || 'spelling',
      start: c.position?.start ?? 0,
      end: c.position?.end ?? 0,
      confidence: c.confidence ?? 0.9,
      explanation: c.explanation,
    })) as Correction[];
  } catch {
    return [];
  }
}
