// Standard response envelope
export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  data?: T;
  errors?: Array<{
    code: string;
    message: string;
    field?: string;
  }>;
  meta?: {
    processing_time_ms?: number;
    tier_used?: string;
  };
}

// Correction types
export interface Correction {
  original: string;
  suggested: string;
  type: 'spelling' | 'grammar' | 'confusion' | 'phonetic' | 'homophone' | 'clarity' | 'style';
  start: number;
  end: number;
  confidence: number;
  explanation?: string;
}

export interface CorrectionResponse {
  corrections: Correction[];
  tier_used: 'quick' | 'deep';
  processing_time_ms: number;
}

// Profile types
export interface ErrorPattern {
  misspelling: string;
  correction: string;
  frequency: number;
  error_type: string;
}

export interface UserProfile {
  user_id: string;
  total_errors: number;
  top_errors: ErrorPattern[];
  confusion_pairs: Array<[string, string]>;
}

// Voice types
export interface TTSResponse {
  audio_url: string;
}

export interface Voice {
  id: string;
  name: string;
  language: string;
}

// Snapshot types
export interface SnapshotData {
  id: string;
  text: string;
  timestamp: number;
  wordCount: number;
}

// Batch correction types
export interface CorrectionLogEntry {
  originalText: string;
  correctedText: string;
  errorType: string;
  context: string;
  confidence: number;
  source?: string;
}

export interface CorrectionBatchResponse {
  logged: number;
  total: number;
}
