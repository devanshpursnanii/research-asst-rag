'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '@/lib/api';
import type { SessionInfo, Paper, Message, QueryMetric } from '@/types';

interface SessionContextType {
  sessionId: string | null;
  sessionInfo: SessionInfo | null;
  papers: Paper[];
  selectedPaperIds: string[];
  messages: Message[];
  queryMetrics: QueryMetric[];
  loading: boolean;
  error: string | null;
  
  // Actions
  createSession: (query: string) => Promise<void>;
  searchPapers: (query: string, searchMode?: 'title' | 'topic') => Promise<void>;
  loadPapers: () => Promise<boolean>;
  sendMessage: (message: string) => Promise<void>;
  togglePaperSelection: (paperId: string) => void;
  refreshSessionInfo: () => Promise<void>;
  clearError: () => void;
  clearPapers: () => void;
  clearChat: () => void;
  resetSession: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    // Load from localStorage on mount
    if (typeof window !== 'undefined') {
      return localStorage.getItem('paperstack_session_id');
    }
    return null;
  });
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [queryMetrics, setQueryMetrics] = useState<QueryMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Persist sessionId to localStorage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('paperstack_session_id', sessionId);
    } else {
      localStorage.removeItem('paperstack_session_id');
    }
  }, [sessionId]);

  // Persist messages to localStorage
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      localStorage.setItem(`paperstack_messages_${sessionId}`, JSON.stringify(messages));
    }
  }, [sessionId, messages]);

  // Restore session data on mount
  useEffect(() => {
    if (typeof window === 'undefined' || !sessionId) return;
    
    const restoreSession = async () => {
      // Restore messages from localStorage
      const savedMessages = localStorage.getItem(`paperstack_messages_${sessionId}`);
      if (savedMessages) {
        try {
          setMessages(JSON.parse(savedMessages));
        } catch (e) {
          console.error('Failed to parse saved messages:', e);
        }
      }

      // Fetch fresh session info from backend (loaded papers, quota, etc.)
      try {
        await refreshSessionInfo();
      } catch (err) {
        // Session expired or invalid - clear it but keep auth token
        console.log('Session not found on backend, clearing stale sessionId');
        localStorage.removeItem('paperstack_session_id');
        localStorage.removeItem(`paperstack_messages_${sessionId}`);
        setSessionId(null);
        setMessages([]);
        setPapers([]);
        setSelectedPaperIds([]);
      }
    };

    restoreSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  const createSession = async (query: string) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.createSession(query);
      
      if (response.error) {
        setError(response.error);
        return;
      }
      
      setSessionId(response.session_id);
      setMessages([]);
      setPapers([]);
      setSelectedPaperIds([]);
      
      // Clear old messages from localStorage
      if (sessionId) {
        localStorage.removeItem(`paperstack_messages_${sessionId}`);
      }
      
      // Fetch session info
      await refreshSessionInfo();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
    } finally {
      setLoading(false);
    }
  };

  const searchPapers = async (query: string, searchMode: 'title' | 'topic' = 'topic') => {
    try {
      setLoading(true);
      setError(null);
      
      // Auto-create session if it doesn't exist (lazy creation)
      let currentSessionId = sessionId;
      if (!currentSessionId) {
        try {
          const response = await api.createSession('Research session');
          if (response.error) {
            setError(response.error);
            return;
          }
          currentSessionId = response.session_id;
          setSessionId(currentSessionId);
          setMessages([]);
          setPapers([]);
          setSelectedPaperIds([]);
        } catch (err) {
          // Silently handle AbortErrors (user navigated away quickly)
          if (err instanceof Error && err.name === 'AbortError') {
            return;
          }
          throw err;
        }
      }

      if (!currentSessionId) {
        setError('Failed to initialize session');
        return;
      }

      try {
        const response = await api.searchPapers(currentSessionId, query, searchMode);
        
        if (response.error) {
          // Check if it's a rate limit error from arXiv
          if (response.error.includes('rate limit')) {
            setError(response.error);
          } else if (response.error.startsWith('quota_exhausted')) {
            setError('Brain search quota exhausted. Please wait for cooldown.');
          } else {
            setError(response.error);
          }
          return;
        }
        
        setPapers(response.papers);
        await refreshSessionInfo();
      } catch (err: any) {
        // Handle 404 - session expired, create new one and retry
        if (err?.status === 404) {
          console.log('Session 404, creating new session and retrying...');
          
          // Clear old session
          localStorage.removeItem('paperstack_session_id');
          if (currentSessionId) {
            localStorage.removeItem(`paperstack_messages_${currentSessionId}`);
          }
          setSessionId(null);
          setMessages([]);
          
          // Create new session
          const newSessionResponse = await api.createSession('Research session');
          if (newSessionResponse.error) {
            setError('Failed to create new session');
            return;
          }
          
          currentSessionId = newSessionResponse.session_id;
          setSessionId(currentSessionId);
          
          // Retry search with new session
          const retryResponse = await api.searchPapers(currentSessionId, query, searchMode);
          if (retryResponse.error) {
            setError(retryResponse.error);
            return;
          }
          
          setPapers(retryResponse.papers);
          await refreshSessionInfo();
          return;
        }
        throw err;
      }
    } catch (err) {
      // Silently handle AbortErrors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to search papers');
    } finally {
      setLoading(false);
    }
  };

  const loadPapers = async () => {
    if (!sessionId || selectedPaperIds.length === 0) {
      setError('No papers selected');
      return false;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await api.loadPapers(sessionId, selectedPaperIds);
      
      if (response.error) {
        setError(response.error);
        return false;
      }
      
      // Clear selected papers after successful load
      setSelectedPaperIds([]);
      await refreshSessionInfo();
      return true;
    } catch (err: any) {
      // Handle 404 - session expired
      if (err?.status === 404) {
        setError('Session expired. Please search for papers again to create a new session.');
        // Clear expired session
        localStorage.removeItem('paperstack_session_id');
        localStorage.removeItem(`paperstack_messages_${sessionId}`);
        setSessionId(null);
        setMessages([]);
        setPapers([]);
        setSelectedPaperIds([]);
        return false;
      }
      setError(err instanceof Error ? err.message : 'Failed to load papers');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (message: string) => {
    if (!sessionId) {
      setError('No active session');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Add user message immediately
      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: message,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, userMessage]);

      // Add loading assistant message with thinking steps placeholder
      const loadingMessageId = (Date.now() + 1).toString();
      const loadingMessage: Message = {
        id: loadingMessageId,
        role: 'assistant',
        content: '',
        thinking_steps: [
          { step: 'routing', status: 'in_progress', result: 'Classifying query intent...' },
          { step: 'retrieval', status: 'pending', result: null },
          { step: 'generation', status: 'pending', result: null },
        ],
        timestamp: new Date(),
        isLoading: true,
      };
      setMessages(prev => [...prev, loadingMessage]);

      try {
        const response = await api.sendMessage(sessionId, message);
      
        if (response.error) {
          // Remove loading message on error
          setMessages(prev => prev.filter(m => m.id !== loadingMessageId));
          
          if (response.error.startsWith('quota_exhausted')) {
            setError('Chat message quota exhausted. Please wait for cooldown.');
          } else {
            setError(response.error);
          }
          return;
        }
      
        // Replace loading message with actual response
        const assistantMessage: Message = {
          id: loadingMessageId,
          role: 'assistant',
          content: response.answer,  // Backend returns 'answer' not 'response'
          thinking_steps: response.thinking_steps,
          citations: response.citations,
          timestamp: new Date(),
        };
        setMessages(prev => prev.map(m => m.id === loadingMessageId ? assistantMessage : m));
      
        await refreshSessionInfo();
      } catch (err: any) {
        // Handle 502 - worker timeout/restart
        if (err?.status === 502) {
          setMessages(prev => prev.filter(m => m.id !== loadingMessageId));
          setError('Server is busy processing your request. Please try again in a moment.');
          return;
        }
        
        // Handle 404 - session expired during chat
        if (err?.status === 404) {
          // Remove loading message
          setMessages(prev => prev.filter(m => m.id !== loadingMessageId));
          setError('Session expired. Please search and load papers again to continue chatting.');
          // Clear expired session
          localStorage.removeItem('paperstack_session_id');
          localStorage.removeItem(`paperstack_messages_${sessionId}`);
          setSessionId(null);
          setMessages([]);
          setPapers([]);
          setSelectedPaperIds([]);
          return;
        }
        
        // Remove loading message on other errors
        setMessages(prev => prev.filter(m => m.id !== loadingMessageId));
        throw err;
      }
    } catch (err) {
      // Catch any unhandled errors
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const togglePaperSelection = (paperId: string) => {
    setSelectedPaperIds(prev =>
      prev.includes(paperId)
        ? prev.filter(id => id !== paperId)
        : [...prev, paperId]
    );
  };

  const clearPapers = () => {
    setPapers([]);
    setSelectedPaperIds([]);
  };

  const resetSession = async () => {
    // Clear all state
    setPapers([]);
    setSelectedPaperIds([]);
    setMessages([]);
    setSessionInfo(null);
    
    // Create new session
    try {
      await createSession('New Session');
    } catch (err) {
      console.error('Failed to create new session:', err);
    }
  };

  const refreshSessionInfo = async () => {
    if (!sessionId) return;

    try {
      const response = await api.getSessionInfo(sessionId);
      if (!response.error) {
        setSessionInfo(response.session_info);
        
        // Update query metrics if available
        if (response.query_metrics) {
          setQueryMetrics(response.query_metrics);
        }
      }
    } catch (err) {
      // If session not found (404), clear it and create a new one
      const is404 = (err as any)?.status === 404 || (err instanceof Error && err.message.includes('404'));
      
      if (is404) {
        // Silently recover from expired session
        setSessionId(null);
        localStorage.removeItem('paperstack_session_id');
        
        // Auto-create new session
        try {
          const newSession = await api.createSession('New Session');
          setSessionId(newSession.session_id);
          localStorage.setItem('paperstack_session_id', newSession.session_id);
          // Fetch info for new session
          const newInfo = await api.getSessionInfo(newSession.session_id);
          if (!newInfo.error) {
            setSessionInfo(newInfo.session_info);
          }
        } catch (createErr) {
          console.error('Failed to create new session:', createErr);
        }
      }
    }
  };

  const clearError = () => setError(null);

  const clearChat = () => {
    // Clear messages from UI and localStorage
    setMessages([]);
    if (sessionId) {
      localStorage.removeItem(`paperstack_messages_${sessionId}`);
    }
    // Session ID and quota remain intact
  };

  return (
    <SessionContext.Provider
      value={{
        sessionId,
        sessionInfo,
        papers,
        selectedPaperIds,
        messages,
        queryMetrics,
        loading,
        error,
        createSession,
        searchPapers,
        loadPapers,
        sendMessage,
        togglePaperSelection,
        refreshSessionInfo,
        clearError,
        clearPapers,
        clearChat,
        resetSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within SessionProvider');
  }
  return context;
}
