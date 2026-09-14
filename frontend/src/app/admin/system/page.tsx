'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import Skeleton from '@/components/Skeleton';
import type { SystemStatus } from '@/types';

const INTEGRATION_LABELS: Record<string, string> = {
  serpapi: 'SerpAPI (search)',
  gemini: 'Gemini (AI assistant)',
  openai: 'OpenAI (AI provider)',
  anthropic: 'Anthropic (AI provider)',
  smtp: 'SMTP (email sending)',
  imap: 'IMAP (reply detection)',
};

function ServiceCard({ name, ok, detail }: { name: string; ok: boolean; detail?: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
      <div className="flex items-center gap-3">
        <span
          className={`inline-block h-3 w-3 rounded-full ${
            ok ? 'bg-green-500' : 'bg-red-500'
          }`}
        />
        <span className="text-sm font-medium text-gray-900 dark:text-white">{name}</span>
        <span
          className={`ml-auto text-xs font-semibold ${
            ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
          }`}
        >
          {ok ? 'UP' : 'DOWN'}
        </span>
      </div>
      {detail && (
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{detail}</p>
      )}
    </div>
  );
}

export default function AdminSystemPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.getAdminSystem();
      setStatus(response.data);
      setError('');
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      setError(
        axiosError.response?.data?.error?.message ||
          axiosError.response?.data?.detail ||
          'Failed to load system status'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  if (isLoading) return <Skeleton rows={3} />;

  if (error || !status) {
    return (
      <div className="rounded-lg bg-red-50 dark:bg-red-900/30 p-4 text-sm text-red-700 dark:text-red-300">
        {error || 'No data'}
        <button onClick={fetchStatus} className="ml-3 underline">
          Retry
        </button>
      </div>
    );
  }

  const configured = Object.entries(status.integrations).filter(([, ok]) => ok);
  const missing = Object.entries(status.integrations).filter(([, ok]) => !ok);

  return (
    <div className="space-y-6">
      {/* Core services */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <ServiceCard name="Database (MariaDB)" ok={status.database} />
        <ServiceCard name="Redis" ok={status.redis} />
        <ServiceCard
          name="Celery workers"
          ok={status.celery_online}
          detail={
            status.celery_workers.length
              ? `Online: ${status.celery_workers.join(', ')}`
              : 'No worker responded to ping (background tasks will not run).'
          }
        />
      </div>

      {/* Integrations */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Integrations
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {Object.entries(status.integrations).map(([key, ok]) => (
            <div
              key={key}
              className="flex items-center gap-3 rounded-md border border-gray-100 dark:border-gray-700 px-3 py-2"
            >
              <span className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
              <span className="text-sm text-gray-800 dark:text-gray-200">
                {INTEGRATION_LABELS[key] || key}
              </span>
              <span
                className={`ml-auto text-xs font-semibold ${
                  ok ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'
                }`}
              >
                {ok ? 'CONFIGURED' : 'NOT CONFIGURED'}
              </span>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-gray-400 dark:text-gray-500">
          Shows whether keys/settings are present on the server - values are never displayed
          and no provider API is called from this page.
        </p>
        {missing.length > 0 && (
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            To configure: add the keys to <code>/opt/smart-reach-ai-staging/.staging.env</code>{' '}
            on the VM, then redeploy (Run workflow) or <code>docker compose up -d</code>.
            {configured.length === 0 && ' Currently no integrations are configured.'}
          </p>
        )}
      </div>
    </div>
  );
}
