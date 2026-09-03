'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { Campaign, CampaignStats } from '@/types';
import ResearchProgress from '@/components/ResearchProgress';
import StatsCards from '@/components/StatsCards';
import Link from 'next/link';

export default function CampaignDetailPage() {
  const params = useParams();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [leadsCount, setLeadsCount] = useState<number>(0);
  const [researchActive, setResearchActive] = useState(false);
  const [isStartingResearch, setIsStartingResearch] = useState(false);

  const fetchCampaign = useCallback(async () => {
    try {
      const response = await api.getCampaign(Number(params.id));
      const data: Campaign = response.data;
      setCampaign(data);
      setResearchActive(data.status === 'researching');

      // Campaign statistics (non-fatal if unavailable)
      try {
        const statsResponse = await api.getCampaignStats(data.id);
        setStats(statsResponse.data as CampaignStats);
      } catch {
        // stats are additive - never block the page on them
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to load campaign';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [params.id]);

  const fetchLeadsCount = useCallback(async () => {
    if (!params.id) return;
    try {
      const response = await api.getLeads({ campaign_id: Number(params.id), per_page: 1 });
      setLeadsCount(response.data.total || 0);
    } catch (err) {
      // Leads might not exist yet, that's okay
      setLeadsCount(0);
    }
  }, [params.id]);

  useEffect(() => {
    if (params.id) {
      fetchCampaign();
      fetchLeadsCount();
    }
  }, [params.id, fetchCampaign, fetchLeadsCount]);

  const handleStartResearch = async () => {
    if (!campaign) return;

    setIsStartingResearch(true);
    try {
      await api.startResearch(campaign.id);
      // Stay on this page and show live research progress.
      setCampaign({ ...campaign, status: 'researching', started_at: new Date().toISOString() });
      setResearchActive(true);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to start research';
      setError(message);
    } finally {
      setIsStartingResearch(false);
    }
  };

  const handleResearchComplete = () => {
    // Refresh campaign (status changed) and the leads count.
    fetchCampaign();
    fetchLeadsCount();
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-300">Loading...</div>
      </main>
    );
  }

  if (error || !campaign) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md">
            {error || 'Campaign not found'}
          </div>
          <Link href="/campaigns" className="text-blue-600 hover:text-blue-700 mt-4 inline-block">
            ← Back to Campaigns
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <Link
              href="/campaigns"
              className="text-blue-600 hover:text-blue-700 font-medium text-sm"
            >
              ← Back to Campaigns
            </Link>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                  {campaign.name}
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  {campaign.description || 'No description'}
                </p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                campaign.status === 'draft' ? 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300' :
                campaign.status === 'researching' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                campaign.status === 'ready' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                campaign.status === 'active' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300' :
                campaign.status === 'paused' ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300' :
                'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300'
              }`}>
                {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
              </span>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Keywords ({campaign.keywords.length})
              </h2>
              <div className="flex flex-wrap gap-2">
                {campaign.keywords.map((keyword, index) => (
                  <span
                    key={index}
                    className="bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 px-3 py-1 rounded-full text-sm"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-6 mt-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Campaign Info
              </h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Created:</span>
                  <span className="ml-2 text-gray-900 dark:text-white">
                    {new Date(campaign.created_at).toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Last Updated:</span>
                  <span className="ml-2 text-gray-900 dark:text-white">
                    {new Date(campaign.updated_at).toLocaleString()}
                  </span>
                </div>
                {campaign.started_at && (
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Started:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">
                      {new Date(campaign.started_at).toLocaleString()}
                    </span>
                  </div>
                )}
                {campaign.completed_at && (
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Completed:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">
                      {new Date(campaign.completed_at).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {error && (
              <div className="mt-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-4 mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
              {/* View Leads Button */}
              <Link
                href={`/leads?campaign_id=${campaign.id}`}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md transition-colors flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                View Leads ({leadsCount})
              </Link>

              {campaign.status === 'draft' && (
                <>
                  <Link
                    href={`/campaigns/${campaign.id}/edit`}
                    className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
                  >
                    Edit Campaign
                  </Link>
                  <button
                    onClick={handleStartResearch}
                    disabled={isStartingResearch}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-2 rounded-md transition-colors"
                  >
                    {isStartingResearch ? 'Starting...' : 'Start Research'}
                  </button>
                </>
              )}
            </div>
          </div>

          {stats && (
            <div className="mt-6">
              <StatsCards
                stats={[
                  { label: 'Websites Found', value: stats.websites_found },
                  { label: 'Websites Crawled', value: stats.websites_crawled },
                  { label: 'Contacts Found', value: stats.contacts_found },
                  { label: 'Leads Created', value: stats.leads_created },
                  { label: 'Emails Sent', value: stats.emails_sent },
                  { label: 'Replies', value: stats.replies_received },
                ]}
              />
            </div>
          )}

          {researchActive && campaign && (
            <ResearchProgress
              campaignId={campaign.id}
              onComplete={handleResearchComplete}
            />
          )}

          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <p className="text-sm text-blue-800 dark:text-blue-300">
              <strong>Note:</strong> Starting research searches the web for each campaign
              keyword, then politely crawls the discovered websites (respecting robots.txt)
              to extract public contact details and create leads for your review.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
