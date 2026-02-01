'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { SessionProvider } from '@/contexts/SessionContext';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    // Check if token exists
    const token = localStorage.getItem('paperstack_token');
    
    if (!token) {
      // No token, redirect to login with return URL
      const currentPath = window.location.pathname;
      router.push(`/?returnUrl=${encodeURIComponent(currentPath)}`);
      return;
    }
  }, [router]);

  return <SessionProvider>{children}</SessionProvider>;
}
