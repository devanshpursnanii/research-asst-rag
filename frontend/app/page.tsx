'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Lock } from 'lucide-react';

export default function LoginPage() {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  // Get API URL from environment
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Check if already authenticated
  useEffect(() => {
    const storedToken = localStorage.getItem('paperstack_token');
    if (storedToken) {
      // Already authenticated, redirect to app
      const returnUrl = searchParams.get('returnUrl') || '/app';
      router.push(returnUrl);
    }
  }, [router, searchParams]);

  const validateToken = async (tokenToValidate: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 20000);

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
        setError('');
        
        // Redirect to original destination or default to /app
        const returnUrl = searchParams.get('returnUrl') || '/app';
        router.push(returnUrl);
      } else {
        setError('Invalid access token');
      }
    } catch (err) {
      console.error('Token validation error:', err);
      setError('Failed to validate token. Please try again.');
    } finally {
      setIsLoading(false);
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

  return (
    <div className="fixed inset-0 bg-black flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
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
  );
}
