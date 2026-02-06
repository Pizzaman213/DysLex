import { api } from './api';
import { runLocalCorrection } from './onnxModel';

export interface Correction {
  original: string;
  suggested: string;
  type: 'spelling' | 'grammar' | 'confusion' | 'phonetic';
  start: number;
  end: number;
  confidence: number;
  explanation?: string;
}

export async function getCorrections(text: string): Promise<Correction[]> {
  // Try local ONNX model first for quick corrections
  const localCorrections = await runLocalCorrection(text);

  if (localCorrections.length > 0) {
    return localCorrections;
  }

  // Fall back to cloud API for deeper analysis
  try {
    const response = await api.getCorrections(text);
    return response.corrections.map((c, i) => ({
      ...c,
      start: 0,
      end: 0,
      confidence: 0.9,
    })) as Correction[];
  } catch {
    return [];
  }
}
