'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import Header from '@/components/Header';

interface Exchange {
  question: string;
  answer: string;
}

const EXAMPLES = [
  'Which leads are interested but have no email sent yet?',
  'How many replies did I get in the last 7 days?',
  'Show me my highest scoring leads',
  'Which campaigns have the most approved leads?',
];

export default function AssistantPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [question, setQuestion] = useState('');
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState('');

  const ask = useCallback(
    async (q: string) => {
      if (!q.trim()) return;
      setIsThinking(true);
      setError('');
      setExchanges((prev) => [...prev, { question: q, answer: '' }]);
      try {
        const response = (await api.askAssistant({ question: q })).data;
        setExchanges((prev) => {
          const next = [...prev];
          next[next.length - 1] = { question: q, answer: response.answer };
          return next;
        });
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
        const message = axiosError.response?.data?.error?.message || 'The assistant is unavailable';
        setExchanges((prev) => {
          const next = [...prev];
          next[next.length - 1] = { question: q, answer: message };
          return next;
        });
      } finally {
        setIsThinking(false);
      }
    },
    []
  );

  useEffect(() => {
    if (isThinking || exchanges.length === 0) return;
    // scroll the latest answer into view
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  }, [exchanges, isThinking]);

  if (authLoading) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-300">Loading...</div>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-300">
          Please{' '}
          <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">
            sign in
          </Link>{' '}
          to use the assistant
        </div>
      </main>
    );
  }

  return (
    <AppShell>
      <Header
        title="AI Sales Assistant"
        description="Ask anything about your campaigns, leads and replies"
        action={
          <Link
            href="/campaigns"
            className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors text-sm"
          >
            Campaigns
          </Link>
        }
      />
      <div className="container mx-auto px-4 py-8 max-w-3xl">
        {exchanges.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              Try asking:
            </p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  onClick={() => ask(example)}
                  disabled={isThinking}
                  className="bg-gray-100 dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1.5 rounded-full text-sm transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          {exchanges.map((exchange, index) => (
            <div key={index} className="space-y-3">
              <div className="flex justify-end">
                <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-[80%] text-sm">
                  {exchange.question}
                </div>
              </div>
              <div className="flex justify-start">
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md px-4 py-3 max-w-[90%] text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                  {isThinking && index === exchanges.length - 1 && !exchange.answer ? (
                    <span className="text-gray-400">Thinking...</span>
                  ) : (
                    exchange.answer
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
          <div className="flex gap-3">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isThinking) ask(question);
              }}
              placeholder="Ask about your leads, campaigns, replies..."
              disabled={isThinking}
              className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-4 py-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
            <button
              onClick={() => ask(question)}
              disabled={isThinking || !question.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-6 py-2 rounded-md transition-colors"
            >
              {isThinking ? '...' : 'Ask'}
            </button>
          </div>
          {error && <p className="text-sm text-red-600 dark:text-red-400 mt-2">{error}</p>}
        </div>
      </div>
    </AppShell>
  );
}
