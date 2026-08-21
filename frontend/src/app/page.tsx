'use client';

import { useAuth } from '@/hooks/useAuth';
import Link from 'next/link';

export default function HomePage() {
  const { isAuthenticated, user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-300">Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
                AI Lead Generation Platform
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                {isAuthenticated && user ? `Welcome, ${user.name || user.email}!` : 'Discover, Qualify, Outreach'}
              </p>
            </div>
            {isAuthenticated ? (
              <Link
                href="/campaigns"
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md transition-colors"
              >
                Dashboard
              </Link>
            ) : (
              <div className="space-x-4">
                <Link
                  href="/login"
                  className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md transition-colors"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>

          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8">
            Discover potential clients, qualify leads with AI, and send personalized outreach campaigns.
          </p>

          <div className="grid md:grid-cols-3 gap-6 mt-12">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="text-blue-600 dark:text-blue-400 mb-4">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Discover</h3>
              <p className="text-gray-600 dark:text-gray-400">
                Search the web for potential clients using targeted keywords
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="text-green-600 dark:text-green-400 mb-4">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Qualify</h3>
              <p className="text-gray-600 dark:text-gray-400">
                AI-powered lead scoring and qualification
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="text-purple-600 dark:text-purple-400 mb-4">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Outreach</h3>
              <p className="text-gray-600 dark:text-gray-400">
                Send personalized email campaigns with human approval
              </p>
            </div>
          </div>

          <div className="mt-12 p-6 bg-blue-600 dark:bg-blue-700 rounded-lg shadow-lg text-white">
            <p className="text-lg mb-2">Implementation Status</p>
            <p className="text-blue-100">
              ✓ Iteration 1.1: Project Setup &nbsp;•&nbsp; ✓ Iteration 1.2: Authentication &nbsp;•&nbsp; ✓ Iteration 1.3: Lead Management
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
