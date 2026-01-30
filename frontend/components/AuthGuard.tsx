'use client';

import { useState, useEffect } from 'react';
import { Lock } from 'lucide-react';

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [isValidating, setIsValidating] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // Get API URL from environment or use localhost
  const API_BASE_URL = typeof window !== 'undefined' 
    ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    : 'http://localhost:8000';

  // Setup browser close handler to clear state
  useEffect(() => {
    const handleBeforeUnload = () => {
      // This fires on both refresh and close, so we use sessionStorage
      // sessionStorage persists on refresh but clears on browser/tab close
      sessionStorage.setItem('paperstack_validated', 'true');
    };

    const handleUnload = () => {
      // Final cleanup - this only runs on actual close
      sessionStorage.removeItem('paperstack_validated');
      localStorage.removeItem('paperstack_token'); // Clear token on browser close
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('unload', handleUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('unload', handleUnload);
    };
  }, []);

  // Check for stored token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('paperstack_token');
    const hasValidated = sessionStorage.getItem('paperstack_validated') === 'true';
    
    // If we've already validated successfully this session, skip validation
    if (hasValidated && storedToken) {
      setIsAuthenticated(true);
      setIsValidating(false);
      return;
    }
    
    if (storedToken) {
      validateToken(storedToken, true); // true = this is a stored token, retry on failure
    } else {
      setIsValidating(false);
    }
  }, []);

  const validateToken = async (tokenToValidate: string, isStoredToken: boolean = false) => {
    const maxRetries = isStoredToken ? 3 : 0; // Retry stored tokens, not user-entered ones
    let retryCount = 0;
    
    while (retryCount <= maxRetries) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 20000); // 20 second timeout for Render cold starts

        const response = await fetch(`${API_BASE_URL}/auth/validate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token: tokenToValidate }),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        const data = await response.json();

        if (data.valid) {
          localStorage.setItem('paperstack_token', tokenToValidate);
          sessionStorage.setItem('paperstack_validated', 'true'); // Mark as validated
          setIsAuthenticated(true);
          setError('');
          return; // Success!
        } else {
          localStorage.removeItem('paperstack_token');
          setIsAuthenticated(false);
          setError('Invalid access token');
          return; // Invalid token, don't retry
        }
      } catch (err) {
        console.error('Token validation error:', err);
        
        // If this is a stored token and we have retries left, try again
        if (isStoredToken && retryCount < maxRetries) {
          retryCount++;
          console.log(`Retrying token validation (${retryCount}/${maxRetries})...`);
          await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s before retry
          continue;
        }
        
        // No more retries or not a stored token
        if (isStoredToken) {
          localStorage.removeItem('paperstack_token');
          setError(''); // Don't show error for expired stored tokens
        } else {
          setError('Failed to validate token. Please try again.');
        }
        setIsAuthenticated(false);
        return;
      } finally {
        setIsValidating(false);
        setIsLoading(false);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) {
      setError('Please enter an access token');
      return;
    }

    setIsLoading(true);
    setError('');
    await validateToken(token.trim());
  };

  // Show loading state while validating stored token
  if (isValidating) {
    return (
      <div className="fixed inset-0 bg-gray-900 flex items-center justify-center">
        <div className="text-white text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Validating access...</p>
        </div>
      </div>
    );
  }

  // Show login overlay if not authenticated
  if (!isAuthenticated) {
    return (
      <>
        {/* Greyscale and blurred background */}
        <div 
          className="fixed inset-0 z-40"
          style={{
            filter: 'grayscale(100%) blur(4px)',
            pointerEvents: 'none',
          }}
        >
          {children}
        </div>

        {/* Dark overlay */}
        <div className="fixed inset-0 bg-black/60 z-50 backdrop-blur-sm" />

        {/* Login modal */}
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 relative">
            {/* Lock icon */}
            <div className="flex justify-center mb-6">
              <div className="bg-gray-900 rounded-full p-4">
                <Lock className="h-8 w-8 text-white" />
              </div>
            </div>

            {/* Title */}
            <h1 className="text-2xl font-bold text-center text-gray-900 mb-2">
              PaperStack Access
            </h1>
            <p className="text-center text-gray-600 mb-4 text-sm">
              This is a demo project. Enter your access token to continue.
            </p>
            <p className="text-center text-gray-500 mb-8 text-xs">
              💼 If you visited this website via my resume, please reopen the resume to find the access token under project description.
            </p>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="token" className="block text-sm font-medium text-gray-700 mb-2">
                  Access Token
                </label>
                <input
                  id="token"
                  type="text"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Enter your access token"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition-all text-gray-900 bg-white"
                  disabled={isLoading}
                  autoFocus
                />
              </div>

              {/* Error message */}
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              {/* Submit button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gray-900 text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Validating...
                  </>
                ) : (
                  'Access PaperStack'
                )}
              </button>
            </form>

            {/* Footer */}
            <p className="text-center text-xs text-gray-500 mt-6">
              Contact the project owner to receive an access token
            </p>
          </div>
        </div>
      </>
    );
  }

  // Authenticated - show the app
  return <>{children}</>;
}
