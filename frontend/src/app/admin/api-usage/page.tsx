'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import Skeleton from '@/components/Skeleton';
import type { ApiUsage, ApiUsageInfo } from '@/types';

function usagePct(used: number | null, limit: number | null): number | null {
  if (!used || !limit) return null;
  return Math.min(100, Math.round((used / limit) * 100));
}

function barColor(pct: number | null): string {
  if (pct === null) return 'bg-gray-400';
  if (pct >= 90) return 'bg-red-500';
  if (pct >= 70) return 'bg-amber-500';
  return 'bg-green-500';
}

function Bar({ pct }: { pct: number | null }) {
  if (pct === null) return null;
  return (
    <div className="mt-3 h-2.5 w-full rounded-full bg-gray-100 dark:bg-gray-700">
      <div
        className={`h-2.5 rounded-full transition-all ${barColor(pct)}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function SourceBadge({ source, error }: { source: 'live' | 'counter'; error: string | null }) {
  if (source === 'live' && !error) {
    return (
      <span className="inline-flex items-center rounded-full bg-green-100 dark:bg-green-900/40 px-2.5 py-0.5 text-xs font-semibold text-green-700 dark:text-green-300">
        live
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center rounded-full bg-amber-100 dark:bg-amber-900/40 px-2.5 py-0.5 text-xs font-semibold text-amber-700 dark:text-amber-300"
      title={error || 'Showing locally tracked usage'}
    >
      local count
    </span>
  );
}

export default function AdminApiUsagePage() {
  const [usage, setUsage] = useState<ApiUsage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchUsage = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.getApiUsage();
      setUsage(response.data);
      setLastUpdated(new Date());
      setError('');
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      setError(
        axiosError.response?.data?.error?.message ||
          axiosError.response?.data?.detail ||
          'Failed to load API usage'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  if (isLoading) return <Skeleton rows={3} />;

  if (error || !usage) {
    return (
      <div className="rounded-lg bg-red-50 dark:bg-red-900/30 p-4 text-sm text-red-700 dark:text-red-300">
        {error || 'No data'}
        <button onClick={fetchUsage} className="ml-3 underline">
          Retry
        </button>
      </div>
    );
  }

  const serp = usage.serpapi;
  const gemini = usage.gemini;
  const serpPct = usagePct(serp.used, serp.limit);
  const geminiPct = usagePct(gemini.used, gemini.limit);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {lastUpdated
            ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
            : ''}
        </p>
        <button
          onClick={fetchUsage}
          className="rounded-md bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 text-sm font-medium text-white transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* SerpAPI - web search usage (live from SerpApi account endpoint) */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5 md:col-span-2">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="7" />
                <path strokeLinecap="round" d="M21 21l-4.35-4.35" />
              </svg>
            </span>
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                SerpAPI - Web search
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">Monthly search quota</p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              {serp.configured ? (
                <SourceBadge source={serp.source} error={serp.error} />
              ) : (
                <span className="text-xs font-semibold text-gray-400">not configured</span>
              )}
            </div>
          </div>

          {serp.configured ? (
            <div className="mt-4">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {serp.used ?? '-'}
                {serp.limit ? (
                  <span className="text-base font-medium text-gray-500 dark:text-gray-400">
                    {' '}
                    / {serp.limit} searches
                  </span>
                ) : (
                  <span className="text-base font-medium text-gray-500 dark:text-gray-400">
                    {' '}
                    searches this month
                  </span>
                )}
              </p>
              <Bar pct={serpPct} />
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                {serp.remaining !== null
                  ? `${serp.remaining} searches left this plan month`
                  : 'Usage this plan month'}
              </p>
              {serp.error && (
                <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                  {serp.error} - showing locally tracked searches until it recovers.
                </p>
              )}
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
              Add SERPAPI_KEY in the backend environment to track search usage.
            </p>
          )}
        </div>

        {/* Gemini - AI provider (self-tracked request counter) */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </span>
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Gemini - AI provider
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">Requests this month</p>
            </div>
          </div>

          {gemini.configured ? (
            <div className="mt-4">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {gemini.used ?? 0}
                {gemini.limit ? (
                  <span className="text-base font-medium text-gray-500 dark:text-gray-400">
                    {' '}
                    / {gemini.limit} requests
                  </span>
                ) : (
                  <span className="text-base font-medium text-gray-500 dark:text-gray-400">
                    {' '}
                    requests
                  </span>
                )}
              </p>
              <Bar pct={geminiPct} />
              {!gemini.limit && (
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Set GEMINI_MONTHLY_LIMIT to show a quota bar.
                </p>
              )}
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
              Add GEMINI_API_KEY in the backend environment to track AI usage.
            </p>
          )}
        </div>

        {/* Email - SMTP sends (from email_log) */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </span>
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Email - SMTP
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">Campaign emails this month</p>
            </div>
          </div>

          {usage.email.configured ? (
            <div className="mt-4">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {usage.email.sent_this_month}
                <span className="text-base font-medium text-gray-500 dark:text-gray-400"> sent</span>
              </p>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                {usage.email.failed_this_month} failed
              </p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
              Add SMTP settings in the backend environment to send email.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
