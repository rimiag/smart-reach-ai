'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import type { CampaignComparison, DashboardStats, ReplyAnalytics, ReplyItem } from '@/types';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import StatsCards from '@/components/StatsCards';
import Skeleton from '@/components/Skeleton';
import EmptyState from '@/components/EmptyState';

export default function DashboardPage() {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [replies, setReplies] = useState<ReplyAnalytics | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignComparison[]>([]);
  const [recentReplies, setRecentReplies] = useState<ReplyItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAll = useCallback(async () => {
    try {
      const [statsRes, repliesRes, campaignsRes, repliesListRes] = await Promise.all([
        api.getDashboardStats(),
        api.getReplyAnalytics(),
        api.getCampaignAnalytics(),
        api.getReplies({ per_page: 5 }),
      ]);
      setStats(statsRes.data as DashboardStats);
      setReplies(repliesRes.data as ReplyAnalytics);
      setCampaigns(campaignsRes.data as CampaignComparison[]);
      setRecentReplies(((repliesListRes.data as RepliesResponse).items || []).slice(0, 5));
      setError('');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchAll();
    }
  }, [isAuthenticated, fetchAll]);

  const funnelStages = stats
    ? [
        { label: 'Websites Found', value: stats.websites_discovered, color: 'bg-slate-400' },
        { label: 'Leads Created', value: stats.leads_total, color: 'bg-indigo-500' },
        { label: 'Approved', value: stats.leads_approved, color: 'bg-emerald-500' },
        { label: 'Emails Sent', value: replies?.emails_sent ?? 0, color: 'bg-blue-500' },
        { label: 'Replies', value: replies?.total_replies ?? 0, color: 'bg-teal-500' },
      ]
    : [];

  if (authLoading || (!isAuthenticated && !authLoading)) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-300">
          Please{' '}
          <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">
            sign in
          </Link>{' '}
          to view your dashboard
        </div>
      </main>
    );
  }

  return (
    <AppShell
      title={`Welcome back${user?.name ? ', ' + user.name : ''} 👋`}
      description="Here's what's happening across your campaigns"
      action={
        <div className="flex items-center gap-3">
          <Link
            href="/assistant"
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            🤖 Ask Assistant
          </Link>
          <Link
            href="/campaigns/new"
            className="bg-gray-900 hover:bg-gray-700 dark:bg-white dark:hover:bg-gray-200 dark:hover:text-gray-900 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            + New Campaign
          </Link>
        </div>
      }
    >
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {isLoading || !stats ? (
        <Skeleton rows={4} />
      ) : (
        <>
          {/* Pipeline funnel */}
          <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            Pipeline
          </h2>
          <div className="flex flex-wrap items-center gap-3 mb-8">
            {funnelStages.map((stage, index) => (
              <div key={stage.label} className="flex items-center gap-3">
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 px-5 py-4 min-w-[130px]">
                  <div className={`h-1.5 w-8 rounded-full ${stage.color} mb-2`} />
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stage.value}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {stage.label}
                  </div>
                </div>
                {index < funnelStages.length - 1 && (
                  <svg className="h-4 w-4 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                )}
              </div>
            ))}
          </div>

          {/* Key stats */}
          <StatsCards
            stats={[
              { label: 'Campaigns', value: stats.campaigns_total },
              { label: 'Active Now', value: stats.campaigns_active },
              { label: 'New Leads', value: stats.leads_new },
              { label: 'Unread Replies', value: replies?.unread_replies ?? 0 },
              { label: 'Reply Rate', value: `${replies?.reply_rate_percent ?? 0}%` },
              { label: 'Websites Crawled', value: stats.websites_crawled },
            ]}
          />

          <div className="grid lg:grid-cols-2 gap-6 mt-8">
            {/* Recent replies */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                  Recent Replies
                </h2>
                <Link href="/replies" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                  View all →
                </Link>
              </div>
              {recentReplies.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No replies yet. Replies to your outreach will appear here.
                </p>
              ) : (
                <div className="space-y-3">
                  {recentReplies.map((reply) => (
                    <Link
                      key={reply.id}
                      href={`/leads/${reply.lead_id}`}
                      className="block rounded-md bg-gray-50 dark:bg-gray-900/50 p-3 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
                    >
                      <div className="flex justify-between items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {reply.from_email}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300">
                          {reply.category.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                        {reply.ai_summary || reply.subject || reply.body}
                      </p>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Campaign snapshot */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-base font-semibold text-gray-900 dark:text-white">Campaigns</h2>
                <Link href="/analytics" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                  Full analytics →
                </Link>
              </div>
              {campaigns.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No campaigns yet.</p>
              ) : (
                <div className="space-y-3">
                  {campaigns.slice(0, 6).map((campaign) => (
                    <Link
                      key={campaign.campaign_id}
                      href={`/campaigns/${campaign.campaign_id}`}
                      className="flex justify-between items-center rounded-md bg-gray-50 dark:bg-gray-900/50 p-3 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
                    >
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {campaign.campaign_name}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {campaign.leads_total} leads · {campaign.websites_discovered} sites
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}

interface RepliesResponse {
  items: ReplyItem[];
  total: number;
}
