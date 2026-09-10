'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import type { CampaignComparison, DashboardStats, ReplyAnalytics } from '@/types';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import Header from '@/components/Header';
import StatsCards from '@/components/StatsCards';

export default function AnalyticsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [replies, setReplies] = useState<ReplyAnalytics | null>(null);
  const [comparison, setComparison] = useState<CampaignComparison[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAll = useCallback(async () => {
    try {
      const [statsRes, repliesRes, comparisonRes] = await Promise.all([
        api.getDashboardStats(),
        api.getReplyAnalytics(),
        api.getCampaignAnalytics(),
      ]);
      setStats(statsRes.data as DashboardStats);
      setReplies(repliesRes.data as ReplyAnalytics);
      setComparison(comparisonRes.data as CampaignComparison[]);
      setError('');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to load analytics');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) fetchAll();
  }, [isAuthenticated, fetchAll]);

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
          to view analytics
        </div>
      </main>
    );
  }

  const categoryEntries = replies ? Object.entries(replies.by_category) : [];

  return (
    <AppShell>
      <Header
        title="Analytics"
        description="Performance across all your campaigns"
        action={
          <Link
            href="/campaigns"
            className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors text-sm"
          >
            Campaigns
          </Link>
        }
      />
      <div className="container mx-auto px-4 py-8">
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="text-center py-12 text-gray-600 dark:text-gray-400">Loading analytics...</div>
        ) : (
          <>
            {/* Reply metrics */}
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              Reply Metrics
            </h2>
            {replies && (
              <StatsCards
                stats={[
                  { label: 'Total Replies', value: replies.total_replies },
                  { label: 'Unread', value: replies.unread_replies },
                  { label: 'Last 7 Days', value: replies.replies_last_7_days },
                  { label: 'Reply Rate', value: `${replies.reply_rate_percent}%` },
                ]}
              />
            )}

            {/* Campaign comparison table */}
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mt-8 mb-3">
              Campaign Comparison
            </h2>
            {comparison.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No campaigns yet - create one and run research to see analytics.
              </p>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-900/50 text-gray-500 dark:text-gray-400">
                    <tr>
                      <th className="text-left px-4 py-3">Campaign</th>
                      <th className="text-left px-4 py-3">Status</th>
                      <th className="text-right px-4 py-3">Leads</th>
                      <th className="text-right px-4 py-3">New</th>
                      <th className="text-right px-4 py-3">Approved</th>
                      <th className="text-right px-4 py-3">Websites</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.map((row) => (
                      <tr key={row.campaign_id} className="border-t border-gray-100 dark:border-gray-700">
                        <td className="px-4 py-3">
                          <Link
                            href={`/campaigns/${row.campaign_id}`}
                            className="text-blue-600 hover:text-blue-700 font-medium"
                          >
                            {row.campaign_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{row.status}</td>
                        <td className="px-4 py-3 text-right text-gray-900 dark:text-white">{row.leads_total}</td>
                        <td className="px-4 py-3 text-right text-gray-900 dark:text-white">{row.leads_new}</td>
                        <td className="px-4 py-3 text-right text-gray-900 dark:text-white">{row.leads_approved}</td>
                        <td className="px-4 py-3 text-right text-gray-900 dark:text-white">
                          {row.websites_discovered}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Category breakdown */}
            {replies && categoryEntries.length > 0 && (
              <>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mt-8 mb-3">
                  Replies by Category
                </h2>
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-3">
                  {categoryEntries.map(([category, count]) => {
                    const maxCount = Math.max(...categoryEntries.map(([, c]) => c));
                    const width = Math.round((count / maxCount) * 100);
                    return (
                      <div key={category}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-700 dark:text-gray-300">
                            {category.replace('_', ' ')}
                          </span>
                          <span className="text-gray-500 dark:text-gray-400">{count}</span>
                        </div>
                        <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${width}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            {/* Empty-state hint */}
            {stats && stats.leads_total === 0 && (
              <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md text-sm text-blue-800 dark:text-blue-300">
                No data yet - create a campaign and run research to populate analytics.
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
