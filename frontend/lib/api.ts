// API Client for FastAPI backend

import type {
  CreateSessionResponse,
  BrainSearchResponse,
  BrainLoadResponse,
  ChatMessageResponse,
  SessionInfoResponse,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

// Get token from localStorage
function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('paperstack_token');
}

// Handle 401 responses by clearing token and reloading
function handleUnauthorized() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('paperstack_token');
  window.location.reload();
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  try {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // Add Authorization header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Merge with any additional headers from options
    const finalHeaders = {
      ...headers,
      ...(options?.headers as Record<string, string> || {}),
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      mode: 'cors',
      credentials: 'include',
      headers: finalHeaders,
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
      handleUnauthorized();
      throw new APIError(401, 'Unauthorized - please log in again');
    }

    if (!response.ok) {
      const errorText = await response.text();
      // Only log non-404 errors (404s are expected during session recovery)
      if (response.status !== 404) {
        console.error(`API Error ${response.status}:`, errorText);
      }
      throw new APIError(response.status, `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    // Only log non-404 errors
    if (error instanceof APIError && error.status !== 404) {
      console.error('API request failed:', error.message);
    } else if (!(error instanceof APIError)) {
      console.error('Network error:', error);
    }
    if (error instanceof APIError) throw error;
    throw new Error(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

export const api = {
  // Create new session
  createSession: async (initialQuery: string): Promise<CreateSessionResponse> => {
    return fetchAPI<CreateSessionResponse>('/session/create', {
      method: 'POST',
      body: JSON.stringify({ initial_query: initialQuery }),
    });
  },

  // Search papers with Paper Brain
  searchPapers: async (sessionId: string, query: string, searchMode: 'title' | 'topic' = 'topic'): Promise<BrainSearchResponse> => {
    return fetchAPI<BrainSearchResponse>('/brain/search', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, query, search_mode: searchMode }),
    });
  },

  // Load selected papers
  loadPapers: async (sessionId: string, paperIds: string[]): Promise<BrainLoadResponse> => {
    return fetchAPI<BrainLoadResponse>('/brain/load', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, paper_ids: paperIds }),
    });
  },

  // Send message to Paper Chat
  sendMessage: async (sessionId: string, message: string): Promise<ChatMessageResponse> => {
    return fetchAPI<ChatMessageResponse>('/chat/message', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  },

  // Get session info and quota status
  getSessionInfo: async (sessionId: string): Promise<SessionInfoResponse> => {
    return fetchAPI<SessionInfoResponse>(`/session/${sessionId}/info`);
  },

  // Health check
  healthCheck: async (): Promise<{ status: string }> => {
    return fetchAPI<{ status: string }>('/health');
  },
};
