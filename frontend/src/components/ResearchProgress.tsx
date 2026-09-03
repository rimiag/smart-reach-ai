'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { ResearchProgress as ResearchProgressData } from '@/types';

const POLL_INTERVAL_MS = 3000;

interface ResearchProgressProps {
  campaignId: number;
  /** Called once when the research run reaches a final state (ready/failed). */
  onComplete?: (status: 'ready' | 'failed') => void;
}

export default function ResearchProgress({ campaignId, onComplete }: ResearchProgressProps) {
  const [progress, setProgress] = useState<ResearchProgressData | null>(null);
  const [error, setError] = useState('');
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const response = await api.getResearchProgress(campaignId);
        if (cancelled) return;

        const data: ResearchProgressData = response.data;
        setProgress(data);
        setError('');

        if (data.status !== 'researching') {
          onCompleteRef.current?.(data.status === 'failed' ? 'failed' : 'ready');
          return; // research finished - stop polling
        }
      } catch (err) {
        if (!cancelled) {
          setError('Failed to load research progress');
        }
      }

      if (!cancelled) {
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    };

    poll();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [campaignId]);

  const isRunning = progress?.status === 'researching';
  const isFailed = progress?.status === 'failed';
  const isComplete = progress?.status === 'ready' || progress?.status === 'active' || progress?.status === 'completed';
  const percentage = Math.min(100, Math.max(0, progress?.progress_percentage ?? 0));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mt-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Research Progress
        </h2>
        {progress && (
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            isFailed
              ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
              : isComplete
                ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
          }`}>
            {isRunning ? 'Researching' : isFailed ? 'Failed' : 'Complete'}
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-3 overflow-hidden">
        <div
          className={`h-3 rounded-full transition-all duration-500 ${
            isFailed
              ? 'bg-red-500'
              : isComplete
                ? 'bg-green-500'
                : 'bg-blue-600 animate-pulse'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {error && (
        <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {progress && (
        <>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {progress.current_step}
            {progress.keywords_total > 0 && (
              <span className="ml-2">
                (keywords {progress.keywords_completed}/{progress.keywords_total})
              </span>
            )}
          </p>

          {progress.error && (
            <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md text-sm">
              {progress.error}
              {isFailed && (
                <p className="mt-1 text-xs">
                  The campaign was reset to draft - you can start research again.
                </p>
              )}
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-gray-50 dark:bg-gray-900/50 rounded-md p-4 text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {progress.websites_found}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Websites Found
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900/50 rounded-md p-4 text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {progress.websites_crawled}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Websites Crawled
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900/50 rounded-md p-4 text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {progress.contacts_found}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Contacts Found
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900/50 rounded-md p-4 text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {progress.leads_created}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Leads Created
              </div>
            </div>
          </div>

          {isComplete && (
            <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md flex items-center justify-between">
              <p className="text-sm text-green-800 dark:text-green-300">
                Research complete - {progress.websites_found} websites discovered,{" "}
                {progress.leads_created} leads created. Review and approve your leads
                to prepare outreach.
              </p>
              <Link
                href={`/leads?campaign_id=${campaignId}`}
                className="ml-4 shrink-0 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm transition-colors"
              >
                View Leads
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}
