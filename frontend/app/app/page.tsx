'use client';

import { useEffect, useState } from 'react';
import { useSession } from '@/contexts/SessionContext';
import Header from '@/components/Header';
import ChatMain from '@/components/ChatMain';
import BrainSidebar from '@/components/BrainSidebar';
import MetricsSidebar from '@/components/MetricsSidebar';
import { Loader2, AlertCircle, X } from 'lucide-react';

export default function Home() {
  const { sessionId, error, loading, createSession, clearError } = useSession();
  const [initializing, setInitializing] = useState(false); // Changed to false - no auto-init

  // Don't auto-create session on mount - let user start when ready
  // Session will be created when user performs first action

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <Header />

      {/* Error Toast */}
      {error && (
        <div className="fixed top-20 right-4 z-50 max-w-md animate-slide-in">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 shadow-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-900">Error</p>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
              <button
                onClick={clearError}
                className="text-red-400 hover:text-red-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Layout - 55% chat | 35% sidebars | 10% padding */}
      <div className="flex flex-1 overflow-hidden justify-center items-center px-[2.5%] py-[2.5%]">
        <div className="flex h-full w-full max-w-[95%] gap-[2.5%]">
          {/* Left: Chat (55% of container) */}
          <div className="w-[55%]">
            <ChatMain />
          </div>

          {/* Right: Sidebars (35% of container) */}
          <div className="w-[35%] flex flex-col gap-[2.5%]">
            {/* Brain Sidebar (73.75% vertical) */}
            <div className="h-[73.75%]">
              <BrainSidebar />
            </div>

            {/* Session Activity Sidebar (23.75% vertical) */}
            <div className="h-[23.75%]">
              <MetricsSidebar />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
