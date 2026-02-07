import { ApiError } from './apiErrors';
import { apiRequestManager } from './apiRequestManager';
import type { ApiResponse, CorrectionBatchResponse } from '@/types/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'dyslex-auth-token';

/**
 * Set JWT token and persist to localStorage
 */
export function setAuthToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

/**
 * Get JWT token from localStorage
 */
export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

// Initialize token from storage on load
let authToken = localStorage.getItem(TOKEN_KEY);

/**
 * Sleep utility for retry logic
 */
async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

interface RequestOptions extends RequestInit {
  retry?: boolean;
  maxRetries?: number;
  retryDelay?: number;
}

/**
 * Make HTTP request with retry logic and exponential backoff
 */
async function requestWithRetry<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const {
    retry = false,
    maxRetries = 3,
    retryDelay = 1000,
    ...fetchOptions
  } = options;

  // Update in-memory token from localStorage if it changed
  authToken = localStorage.getItem(TOKEN_KEY);

  for (let attempt = 0; attempt <= (retry ? maxRetries : 0); attempt++) {
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(fetchOptions.headers as Record<string, string> | undefined),
      };

      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...fetchOptions,
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(response.status, errorData);
      }

      return response.json();
    } catch (error) {
      // Determine if error is retryable
      const isRetryable = error instanceof ApiError && error.status >= 500;
      const shouldRetry = retry && isRetryable && attempt < maxRetries;

      if (!shouldRetry) {
        throw error;
      }

      // Exponential backoff
      const backoffMs = retryDelay * Math.pow(2, attempt);
      console.log(`[API] Retry ${attempt + 1}/${maxRetries} after ${backoffMs}ms`);
      await sleep(backoffMs);
    }
  }

  throw new Error('Request failed after retries');
}

/**
 * Legacy request function for backward compatibility
 * New code should use requestWithRetry directly
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  return requestWithRetry<T>(endpoint, options);
}

export const api = {
  // -----------------------------------------------------------------------
  // Auth
  // -----------------------------------------------------------------------
  register: (email: string, name: string, password: string) =>
    request<{ status: string; data: { access_token: string; user_id: string } }>(
      '/api/v1/auth/register',
      { method: 'POST', body: JSON.stringify({ email, name, password }) },
    ),

  login: (email: string, password: string) =>
    request<{ status: string; data: { access_token: string; user_id: string } }>(
      '/api/v1/auth/login',
      { method: 'POST', body: JSON.stringify({ email, password }) },
    ),

  refreshToken: (token: string) =>
    request<{ status: string; data: { access_token: string; user_id: string } }>(
      '/api/v1/auth/refresh',
      { method: 'POST', body: JSON.stringify({ token }) },
    ),

  // -----------------------------------------------------------------------
  // Capture Mode
  // -----------------------------------------------------------------------
  transcribeAudio: async (audioBlob: Blob): Promise<{ transcript: string; language?: string; duration?: number }> => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    const headers: Record<string, string> = {};
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE}/api/v1/capture/transcribe`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Transcription failed: ${response.status}`);
    }

    return response.json();
  },

  extractIdeas: (transcript: string) =>
    request<{ cards: Array<{
      id: string;
      title: string;
      body: string;
      sub_ideas?: Array<{ id: string; title: string; body: string }>;
    }>; topic?: string; clusterNames?: Record<string, string> }>(
      '/api/v1/capture/extract-ideas',
      { method: 'POST', body: JSON.stringify({ transcript }) },
    ),

  extractIdeasFromImage: (imageBase64: string, mimeType: string = 'image/jpeg', hint?: string) =>
    requestWithRetry<{ cards: Array<{
      id: string;
      title: string;
      body: string;
      sub_ideas?: Array<{ id: string; title: string; body: string }>;
    }>; topic?: string }>(
      '/api/v1/vision/extract-ideas',
      {
        method: 'POST',
        body: JSON.stringify({ image_base64: imageBase64, mime_type: mimeType, hint }),
        retry: true,
      },
    ),

  // -----------------------------------------------------------------------
  // Corrections
  // -----------------------------------------------------------------------
  getCorrections: (text: string, mode: string = 'auto') => {
    const signal = apiRequestManager.startRequest('corrections');
    return requestWithRetry<{ status: string; data: { corrections: Array<any> }; meta: Record<string, any> }>(
      `/api/v1/correct/${mode}`,
      {
        method: 'POST',
        body: JSON.stringify({ text, mode }),
        signal,
        retry: true,
      },
    );
  },

  getQuickCorrections: (text: string) =>
    request<{ status: string; data: { corrections: Array<any> } }>(
      '/api/v1/correct/quick',
      { method: 'POST', body: JSON.stringify({ text }) },
    ),

  getDeepCorrections: (text: string, context?: string) =>
    request<{ status: string; data: { corrections: Array<any> } }>(
      '/api/v1/correct/deep',
      { method: 'POST', body: JSON.stringify({ text, context }) },
    ),

  getDocumentReview: (text: string) =>
    request<{ status: string; data: { corrections: Array<any> } }>(
      '/api/v1/correct/document',
      { method: 'POST', body: JSON.stringify({ text }) },
    ),

  deepAnalysis: async (text: string) => {
    interface BackendCorrection {
      original: string;
      correction: string;
      error_type: string;
      explanation?: string;
      position: {
        start: number;
        end: number;
      };
    }

    const response = await requestWithRetry<{
      status: string;
      data: { corrections: BackendCorrection[] };
      meta: { processing_time_ms: number; tier_used: string };
    }>('/api/v1/correct/document', {
      method: 'POST',
      body: JSON.stringify({ text, mode: 'document' }),
      retry: true,
    });

    // Generate unique IDs
    const generateId = () => Math.random().toString(36).substr(2, 9);

    // Map error types to categories
    const mapErrorTypeToCategory = (errorType: string): string => {
      const mapping: Record<string, string> = {
        spelling: 'spelling',
        grammar: 'grammar',
        homophone: 'homophone',
        clarity: 'clarity',
        style: 'style',
        punctuation: 'grammar',
        word_choice: 'style',
      };
      return mapping[errorType.toLowerCase()] || 'spelling';
    };

    // Determine change type
    const getChangeType = (original: string, correction: string): 'insert' | 'delete' | 'replace' => {
      if (!original || original.trim() === '') return 'insert';
      if (!correction || correction.trim() === '') return 'delete';
      return 'replace';
    };

    // Filter out corrections without position data (can't be applied without positions)
    // and map backend format to frontend TrackedChange format
    return response.data.corrections
      .filter((c) => c.position && c.position.start != null && c.position.end != null)
      .map((c) => ({
        id: generateId(),
        type: getChangeType(c.original, c.correction),
        original: c.original,
        text: c.correction,
        start: c.position.start,
        end: c.position.end,
        explanation: c.explanation || `Suggested ${mapErrorTypeToCategory(c.error_type)} correction`,
        category: mapErrorTypeToCategory(c.error_type),
      }));
  },

  // -----------------------------------------------------------------------
  // Error Profile
  // -----------------------------------------------------------------------
  getErrorProfile: (userId: string) =>
    request<any>(`/api/v1/profile/${userId}`),

  getTopErrors: (userId: string, limit: number = 20) =>
    request<any>(`/api/v1/profile/${userId}/top-errors?limit=${limit}`),

  getConfusionPairs: (userId: string) =>
    request<any>(`/api/v1/profile/${userId}/confusion-pairs`),

  getProfileProgress: (userId: string) =>
    request<any>(`/api/v1/profile/${userId}/progress`),

  addToDictionary: (userId: string, word: string) =>
    request<any>(`/api/v1/profile/${userId}/dictionary`, {
      method: 'PUT',
      body: JSON.stringify({ word }),
    }),

  getLlmContext: (userId: string) =>
    request<any>(`/api/v1/profile/${userId}/llm-context`),

  getUserCorrectionDict: (userId: string) =>
    request<{ status: string; data: { correction_dict: Record<string, string>; count: number } }>(
      `/api/v1/profile/${userId}/correction-dict`,
    ),

  // -----------------------------------------------------------------------
  // Progress
  // -----------------------------------------------------------------------
  getProgress: () => request<any>('/api/v1/progress'),

  getProgressDashboard: (weeks: number = 12) =>
    request<{ status: string; data: import('../types/progress').ProgressDashboardResponse }>(
      `/api/v1/progress/dashboard?weeks=${weeks}`,
    ),

  // -----------------------------------------------------------------------
  // Voice
  // -----------------------------------------------------------------------
  textToSpeech: (text: string, voice: string = 'default') =>
    request<{ status: string; data: { audio_url: string } }>('/api/v1/voice/speak', {
      method: 'POST',
      body: JSON.stringify({ text, voice }),
    }),

  textToSpeechBatch: (
    sentences: Array<{ index: number; text: string }>,
    voice: string = 'default',
    signal?: AbortSignal,
  ) =>
    requestWithRetry<{
      status: string;
      data: {
        results: Array<{ index: number; audio_url: string; cached: boolean }>;
      };
    }>('/api/v1/voice/speak-batch', {
      method: 'POST',
      body: JSON.stringify({ sentences, voice }),
      signal,
      retry: true,
    }),

  transcribeVoice: async (audioBlob: Blob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    const headers: Record<string, string> = {};
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE}/api/v1/voice/transcribe`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) throw new Error(`Voice transcribe failed: ${response.status}`);
    return response.json();
  },

  getVoices: () => request<any>('/api/v1/voice/voices'),

  // -----------------------------------------------------------------------
  // Adaptive Learning
  // -----------------------------------------------------------------------
  submitSnapshot: (text: string, documentId?: string) =>
    request<any>('/api/v1/snapshots', {
      method: 'POST',
      body: JSON.stringify({ text, document_id: documentId }),
    }),

  getLearningStats: (userId: string) =>
    request<any>(`/api/v1/learn/stats/${userId}`),

  triggerRetrain: () =>
    request<any>('/api/v1/learn/trigger-retrain', { method: 'POST' }),

  // -----------------------------------------------------------------------
  // Passive Learning (legacy log endpoint)
  // -----------------------------------------------------------------------
  logCorrection: (data: {
    originalText: string;
    correctedText: string;
    errorType?: string;
    context?: string;
    confidence?: number;
  }) =>
    request('/api/v1/log-correction', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /**
   * Log multiple corrections in a single batch
   * Improves efficiency for passive learning
   */
  logCorrectionBatch: (corrections: Array<{
    originalText: string;
    correctedText: string;
    errorType: string;
    context: string;
    confidence: number;
    source?: string;
  }>) =>
    requestWithRetry<ApiResponse<CorrectionBatchResponse>>('/api/v1/log-correction/batch', {
      method: 'POST',
      body: JSON.stringify({ corrections }),
      retry: true,
    }),

  // -----------------------------------------------------------------------
  // Users
  // -----------------------------------------------------------------------
  getUser: (userId: string) => request<any>(`/api/v1/users/${userId}`),

  // Settings
  getSettings: (userId: string) =>
    request<{ status: string; data: import('@/types').UserSettings }>(
      `/api/v1/users/${userId}/settings`
    ),

  updateSettings: (userId: string, settings: Partial<import('@/types').UserSettings>) =>
    request<{ status: string; data: import('@/types').UserSettings }>(
      `/api/v1/users/${userId}/settings`,
      {
        method: 'PUT',
        body: JSON.stringify(settings),
      }
    ),

  // Data export and deletion (GDPR)
  exportUserData: async (userId: string): Promise<Blob> => {
    const response = await request<{
      status: string;
      data: {
        user: any;
        settings: any;
        error_profile: any;
        error_logs: any[];
      };
    }>(`/api/v1/users/${userId}/export`);

    return new Blob([JSON.stringify(response.data, null, 2)], {
      type: 'application/json',
    });
  },

  deleteUserData: (userId: string) =>
    request<void>(`/api/v1/users/${userId}`, { method: 'DELETE' }),

  // Deprecated - use getSettings/updateSettings instead
  updateUserSettings: (userId: string, settings: Record<string, any>) =>
    request<any>(`/api/v1/users/${userId}/settings`, {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),

  deleteUser: (userId: string) =>
    request<any>(`/api/v1/users/${userId}`, { method: 'DELETE' }),

  // -----------------------------------------------------------------------
  // Documents & Folders
  // -----------------------------------------------------------------------
  listDocuments: () =>
    request<{
      status: string;
      data: {
        documents: Array<{
          id: string;
          title: string;
          content: string;
          mode: string;
          folder_id: string | null;
          sort_order: number;
          created_at: string | null;
          updated_at: string | null;
        }>;
        folders: Array<{
          id: string;
          name: string;
          sort_order: number;
          created_at: string | null;
          updated_at: string | null;
        }>;
      };
    }>('/api/v1/documents'),

  createDocument: (doc: {
    id: string;
    title?: string;
    content?: string;
    mode?: string;
    folder_id?: string | null;
    sort_order?: number;
  }) =>
    request<{ status: string; data: any }>('/api/v1/documents/docs', {
      method: 'POST',
      body: JSON.stringify(doc),
    }),

  updateDocument: (id: string, updates: {
    title?: string;
    content?: string;
    mode?: string;
    folder_id?: string | null;
    sort_order?: number;
  }) =>
    request<{ status: string; data: any }>(`/api/v1/documents/docs/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    }),

  deleteDocument: (id: string) =>
    request<void>(`/api/v1/documents/docs/${id}`, { method: 'DELETE' }),

  createFolder: (folder: {
    id: string;
    name?: string;
    sort_order?: number;
  }) =>
    request<{ status: string; data: any }>('/api/v1/documents/folders', {
      method: 'POST',
      body: JSON.stringify(folder),
    }),

  updateFolder: (id: string, updates: { name?: string; sort_order?: number }) =>
    request<{ status: string; data: any }>(`/api/v1/documents/folders/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    }),

  deleteFolder: (id: string) =>
    request<void>(`/api/v1/documents/folders/${id}`, { method: 'DELETE' }),

  syncDocuments: (payload: {
    documents: Array<{
      id: string;
      title: string;
      content: string;
      mode: string;
      folder_id: string | null;
      sort_order: number;
    }>;
    folders: Array<{
      id: string;
      name: string;
      sort_order: number;
    }>;
  }) =>
    request<{ status: string; data: { folders_synced: number; documents_synced: number } }>(
      '/api/v1/documents/sync',
      { method: 'PUT', body: JSON.stringify(payload) },
    ),

  // -----------------------------------------------------------------------
  // Coach
  // -----------------------------------------------------------------------
  coachChat: (
    message: string,
    writingContext?: string,
    sessionStats?: { totalWordsWritten: number; timeSpent: number; correctionsApplied: number },
  ) =>
    request<{ status: string; data: { reply: string } }>('/api/v1/coach/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        writing_context: writingContext,
        session_stats: sessionStats,
      }),
    }),

  // -----------------------------------------------------------------------
  // Scaffold
  // -----------------------------------------------------------------------
  generateScaffold: (data: {
    topic: string;
    essayType?: string;
    existingIdeas?: string[];
  }) =>
    request<{
      sections: Array<{
        id: string;
        title: string;
        type: string;
        suggested_topic_sentence?: string;
        hints?: string[];
        order: number;
      }>;
      transitions?: string[];
    }>('/api/v1/scaffold', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // -----------------------------------------------------------------------
  // Mind Map
  // -----------------------------------------------------------------------
  suggestConnections: async (
    nodes: Array<{ id: string; title: string; body: string; cluster: number; x: number; y: number }>,
    edges: Array<{ id: string; source: string; target: string }>,
  ) => {
    return request<{
      suggestions: Array<{
        id: string;
        type: 'connection' | 'gap' | 'cluster';
        sourceNodeId?: string;
        targetNodeId?: string;
        description: string;
        confidence?: number;
      }>;
      clusterNames?: Record<string, string>;
    }>('/api/v1/mindmap/suggest-connections', {
      method: 'POST',
      body: JSON.stringify({ nodes, edges }),
    });
  },

  buildScaffold: async (
    nodes: Array<{ id: string; title: string; body: string; cluster: number; x: number; y: number }>,
    edges: Array<{ id: string; source: string; target: string }>,
    writingGoal?: string,
  ) => {
    return request<{
      title: string;
      sections: Array<{
        heading: string;
        hint: string;
        nodeIds: string[];
        suggestedContent?: string;
      }>;
    }>('/api/v1/mindmap/build-scaffold', {
      method: 'POST',
      body: JSON.stringify({ nodes, edges, writing_goal: writingGoal }),
    });
  },
};
