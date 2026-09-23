'use client';

import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { api } from '@/lib/api';

type VerifyStatus = 'loading' | 'success' | 'invalid' | 'error';

function VerifyEmailInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  const [status, setStatus] = useState<VerifyStatus>('loading');
  const [resent, setResent] = useState(false);
  const [resendError, setResendError] = useState('');
  const [resendEmail, setResendEmail] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('invalid');
      return;
    }
    let cancelled = false;
    api.verifyEmail(token).then(
      () => {
        if (!cancelled) setStatus('success');
      },
      (err: unknown) => {
        if (cancelled) return;
        const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
        const message = axiosError.response?.data?.error?.message || '';
        if (message.includes('Invalid verification link')) {
          setStatus('invalid');
        } else {
          setStatus('error');
        }
      }
    );
    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleResend = async () => {
    setResent(false);
    setResendError('');
    if (!resendEmail) {
      setResendError('Enter the email you signed up with.');
      return;
    }
    try {
      await api.resendVerification(resendEmail);
      setResent(true);
    } catch {
      setResendError('Could not resend right now - please try again in a minute.');
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 text-center">
          {status === 'loading' && (
            <>
              <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
              <p className="text-gray-600 dark:text-gray-400">Verifying your email...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/40">
                <svg className="h-7 w-7 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Email verified</h1>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Your account is ready. You can sign in now.
              </p>
              <Link
                href="/login"
                className="inline-block w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-md transition-colors"
              >
                Sign in
              </Link>
            </>
          )}

          {(status === 'invalid' || status === 'error') && (
            <>
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/40">
                <svg className="h-7 w-7 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {status === 'invalid' ? 'Link invalid or expired' : 'Something went wrong'}
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                {status === 'invalid'
                  ? 'This confirmation link is invalid or has expired (links last 24 hours).'
                  : 'We could not verify your email right now. Please try again.'}
              </p>

              {resent ? (
                <div className="mb-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-600 dark:text-green-400 px-4 py-3 rounded-md text-sm">
                  Verification email sent again - check your inbox.
                </div>
              ) : (
                <div className="space-y-3 text-left">
                  <label htmlFor="resendEmail" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Request a new link
                  </label>
                  <input
                    id="resendEmail"
                    type="email"
                    value={resendEmail}
                    onChange={(e) => setResendEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="you@example.com"
                  />
                  <button
                    type="button"
                    onClick={handleResend}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-md transition-colors"
                  >
                    Resend verification email
                  </button>
                </div>
              )}
              {resendError && (
                <p className="mt-3 text-sm text-red-600 dark:text-red-400">{resendError}</p>
              )}

              <p className="mt-6 text-sm text-gray-600 dark:text-gray-400">
                <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">
                  Back to sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
          <div className="animate-pulse text-sm text-gray-500 dark:text-gray-400">Loading...</div>
        </main>
      }
    >
      <VerifyEmailInner />
    </Suspense>
  );
}
