'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Clock, FileText } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';
import ThinkingSteps from './ThinkingSteps';

export default function ChatMain() {
  const {
    sessionInfo,
    messages,
    loading,
    sendMessage,
    clearChat,
    resetSession,
  } = useSession();

  const [input, setInput] = useState('');
  const [citationsOpen, setCitationsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const chatQuota = sessionInfo?.quota_status.chat;
  const isDisabled = chatQuota && !chatQuota.allowed;
  const hasPapersLoaded = sessionInfo?.loaded_papers && sessionInfo.loaded_papers.length > 0;

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || isDisabled || !hasPapersLoaded) return;

    const message = input;
    setInput('');
    await sendMessage(message);
  };

  const citations = messages
    .filter((m) => m.role === 'assistant' && m.citations)
    .flatMap((m) => m.citations || []);

  return (
    <div className="flex h-full flex-col rounded-xl shadow-lg bg-white relative border-2 border-gray-400 overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex flex-col items-center gap-1 flex-1">
            <h2 className="text-xl font-serif font-semibold text-gray-900">PaperChat</h2>
            <span className="text-sm text-gray-500">
              {chatQuota ? `${chatQuota.messages_remaining}/${chatQuota.messages_used + chatQuota.messages_remaining}` : '5/5'} messages left
            </span>
          </div>
          {messages.length > 0 && (
            <button
              onClick={() => {
                if (confirm('Clear chat messages? (Session and limits remain intact)')) {
                  clearChat();
                }
              }}
              className="px-3 py-1.5 text-xs font-medium text-gray-700 hover:text-gray-900 border-2 border-gray-300 hover:border-gray-400 rounded-lg transition-all mr-2"
              title="Clear chat messages only"
            >
              Clear Chat
            </button>
          )}
          <div className="flex-shrink-0">
            <button
              onClick={() => setCitationsOpen(!citationsOpen)}
              disabled={citations.length === 0}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border-2 border-gray-300 bg-white hover:bg-gray-50 hover:border-gray-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
            >
              <FileText className="h-4 w-4 text-gray-700 group-hover:text-gray-900" />
              <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900">Citations</span>
              {citations.length > 0 && (
                <span className="ml-1 px-2 py-0.5 rounded-full bg-gray-900 text-white text-xs font-semibold">
                  {citations.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Citations Slide-over */}
      <div
        className={`absolute top-0 left-0 w-[400px] h-full bg-white border-r-2 border-gray-400 shadow-2xl transition-transform duration-300 ease-in-out z-20 ${
          citationsOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Drawer Header */}
          <div className="border-b border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-serif font-semibold text-gray-900">Citations</h3>
              <button
                onClick={() => setCitationsOpen(false)}
                className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {new Set(citations.map((c) => c.paper)).size} papers • {citations.length} citations
            </p>
          </div>

          {/* Citations List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {citations.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No citations yet</p>
              </div>
            ) : (
              citations.map((citation, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 transition-colors">
                  <p className="text-sm font-medium text-gray-900 mb-1">{citation.paper}</p>
                  <p className="text-xs text-gray-600">Page {citation.page}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Cooldown Overlay */}
      {isDisabled && chatQuota && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="rounded-lg bg-white p-6 shadow-lg">
            <div className="flex items-center gap-3">
              <Clock className="h-5 w-5 text-gray-900 animate-pulse" />
              <div>
                <p className="font-medium text-gray-900">Cooldown Active</p>
                <p className="text-sm text-gray-600">
                  Available in {chatQuota.cooldown_minutes} minutes
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center">
            <div className="max-w-md space-y-4">
              {!hasPapersLoaded ? (
                <>
                  <div className="w-16 h-16 mx-auto rounded-full bg-gray-100 flex items-center justify-center">
                    <FileText className="h-8 w-8 text-gray-400" />
                  </div>
                  <div>
                    <p className="text-base font-medium text-gray-900 mb-2">
                      No Papers Loaded
                    </p>
                    <p className="text-sm text-gray-500 mb-1">
                      Use PaperBrain to search and load papers first.
                    </p>
                    <p className="text-xs text-gray-400">
                      Then you can ask questions and get answers with citations.
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-sm text-gray-500 mb-2">
                    Papers loaded! Start chatting.
                  </p>
                  <p className="text-xs text-gray-400">
                    Ask questions about your research papers and get answers with citations.
                  </p>
                </>
              )}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                {message.role === 'assistant' && message.thinking_steps && (
                  <ThinkingSteps steps={message.thinking_steps} />
                )}
                {message.isLoading ? (
                  <div className="flex flex-col gap-2 py-2">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Generating response...</span>
                    </div>
                    <p className="text-xs text-gray-400">
                      This may take 1-2 minutes for complex queries
                    </p>
                  </div>
                ) : (
                  <div className="text-sm whitespace-pre-wrap break-words">
                    {(message.content || '').split('\n').map((line, i) => {
                      // Handle bullet points
                      if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
                        return (
                          <div key={i} className="ml-4 my-1">
                            {line}
                          </div>
                        );
                      }
                      // Handle numbered lists
                      if (/^\d+\./.test(line.trim())) {
                        return (
                          <div key={i} className="ml-4 my-1">
                            {line}
                          </div>
                        );
                      }
                      // Handle bold text with **text**
                      const boldFormatted = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                      // Handle code blocks with `code`
                      const codeFormatted = boldFormatted.replace(/`([^`]+)`/g, '<code class="bg-gray-200 px-1 rounded">$1</code>');
                      
                      return (
                        <div key={i} className={line.trim() === '' ? 'h-4' : 'my-1'} dangerouslySetInnerHTML={{ __html: codeFormatted }} />
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        {!hasPapersLoaded && (
          <div className="mb-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-xs text-amber-800">
              ⚠️ Load papers from PaperBrain before chatting
            </p>
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              !hasPapersLoaded
                ? 'Load papers first...'
                : isDisabled
                ? 'Waiting for cooldown...'
                : 'Ask about your papers...'
            }
            disabled={loading || isDisabled || !hasPapersLoaded}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-900 focus:border-gray-900 focus:outline-none focus:ring-1 focus:ring-gray-900 disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={loading || isDisabled || !input.trim() || !hasPapersLoaded}
            className="flex items-center justify-center rounded-lg bg-gray-900 px-4 py-2 text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
