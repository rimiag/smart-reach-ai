'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import type { Campaign, CampaignComparison, DashboardStats } from '@/types';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import StatsCards from '@/components/StatsCards';
import StatusBadge from '@/components/StatusBadge';
import Skeleton from '@/components/Skeleton';
import EmptyState from '@/components/EmptyState';

export default function CampaignsPage() {
  const { isAuthenticated } = useAuth();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [comparison, setComparison] = useState<CampaignComparison[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAll = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const response = await api.getCampaigns();
      setCampaigns(response.data.items || []);
      setError('');

      try {
        const [statsRes, comparisonRes] = await Promise.all([
          api.getDashboardStats(),
          api.getCampaignAnalytics(),
        ]);
        setStats(statsRes.data as DashboardStats);
        setComparison(comparisonRes.data as CampaignComparison[]);
      } catch {
        // stats are additive - never block the campaign list on them
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to load campaigns');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const statsFor = (campaignId: number): CampaignComparison | undefined =>
    comparison.find((row) => row.campaign_id === campaignId);

  if (!isAuthenticated) {
    return (
      <AppShell title="Campaigns">
        <EmptyState
          title="Sign in required"
          message="Sign in to manage your lead generation campaigns."
          action={
            <Link
              href="/login"
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md text-sm font-medium"
            >
              Sign in
            </Link>
          }
        />
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Campaigns"
      description="Create campaigns, run AI research and manage outreach"
      action={
        <Link
          href="/campaigns/new"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
        >
          + New Campaign
        </Link>
      }
    >
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {/* Key stats */}
      {stats && !isLoading && (
        <div className="mb-8">
          <StatsCards
            stats={[
              { label: 'Campaigns', value: stats.campaigns_total },
              { label: 'Active Now', value: stats.campaigns_active },
              { label: 'Total Leads', value: stats.leads_total },
              { label: 'New Leads', value: stats.leads_new },
              { label: 'Approved', value: stats.leads_approved },
              { label: 'Websites Found', value: stats.websites_discovered },
              { label: 'Websites Crawled', value: stats.websites_crawled },
            ]}
          />
        </div>
      )}

      {isLoading ? (
        <Skeleton rows={4} />
      ) : campaigns.length === 0 ? (
        <EmptyState
          icon={
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          }
          title="No campaigns yet"
          message="Create your first campaign to start discovering leads."
          action={
            <Link
              href="/campaigns/new"
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md text-sm font-medium"
            >
              Create your first campaign
            </Link>
          }
        />
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          {campaigns.map((campaign) => {
            const row = statsFor(campaign.id);
            const locations = Array.isArray(
              (campaign.settings || {}).locations
            )
              ? ((campaign.settings || {}).locations as string[])
              : [];
            return (
              <div
                key={campaign.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow flex flex-col"
              >
                <div className="flex justify-between items-start mb-3">
                  <Link
                    href={`/campaigns/${campaign.id}`}
                    className="text-lg font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    {campaign.name}
                  </Link>
                  <StatusBadge status={campaign.status} size="md" />
                </div>

                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                  {campaign.description || 'No description'}
                </p>

                <div className="flex flex-wrap gap-1.5 mb-4">
                  {campaign.keywords.slice(0, 4).map((keyword, idx) => (
                    <span
                      key={idx}
                      className="bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 px-2 py-0.5 rounded text-xs"
                    >
                      {keyword}
                    </span>
                  ))}
                  {campaign.keywords.length > 4 && (
                    <span className="text-gray-500 dark:text-gray-400 text-xs">
                      +{campaign.keywords.length - 4} more
                    </span>
                  )}
                </div>

                {/* Per-campaign metrics from the comparison data */}
                <div className="grid grid-cols-3 gap-2 text-center mb-4">
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-md py-2">
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {row?.leads_total ?? 0}
                    </div>
                    <div className="text-[11px] text-gray-500 dark:text-gray-400">Leads</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-md py-2">
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {row?.leads_new ?? 0}
                    </div>
                    <div className="text-[11px] text-gray-500 dark:text-gray-400">New</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-md py-2">
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {row?.websites_discovered ?? 0}
                    </div>
                    <div className="text-[11px] text-gray-500 dark:text-gray-400">Sites</div>
                  </div>
                </div>

                <div className="mt-auto pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    Created {new Date(campaign.created_at).toLocaleDateString()}
                  </span>
                  <Link
                    href={`/campaigns/${campaign.id}`}
                    className="text-sm font-medium text-blue-600 hover:text-blue-700"
                  >
                    Open →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
