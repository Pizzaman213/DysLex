const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Corrections
  getCorrections: (text: string) =>
    request<{ corrections: Array<{ original: string; suggested: string; type: string }> }>(
      '/api/corrections',
      { method: 'POST', body: JSON.stringify({ text }) }
    ),

  // Error Profile
  getErrorProfile: () => request<any>('/api/profiles/me'),

  updateErrorProfile: (data: any) =>
    request('/api/profiles/me', { method: 'PATCH', body: JSON.stringify(data) }),

  // Progress
  getProgress: () => request<any>('/api/progress'),

  // Voice
  textToSpeech: (text: string) =>
    request<{ audioUrl: string }>('/api/voice/tts', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
};
