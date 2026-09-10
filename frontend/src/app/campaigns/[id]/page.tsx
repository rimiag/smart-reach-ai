'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { Campaign, CampaignStats } from '@/types';
import ResearchProgress from '@/components/ResearchProgress';
import StageIndicator from '@/components/StageIndicator';
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
  const [aiMessage, setAiMessage] = useState('');
  const [showLocationModal, setShowLocationModal] = useState(false);
  const [locationsInput, setLocationsInput] = useState('');

  const stageIndex =
    {
      draft: 0,
      researching: 1,
      ready: 2,
      active: 3,
      paused: 3,
      completed: 4,
    }[campaign?.status ?? 'draft'] ?? 0;

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

  const handleStartResearch = () => {
    if (!campaign) return;
    // Prefill with any locations saved on the campaign
    const saved = ((campaign.settings || {}) as Record<string, unknown>).locations;
    setLocationsInput(Array.isArray(saved) ? saved.join(', ') : '');
    setError('');
    setShowLocationModal(true);
  };

  const handleConfirmStartResearch = async () => {
    if (!campaign) return;

    const locations = locationsInput
      .split(',')
      .map((loc) => loc.trim())
      .filter(Boolean);

    setIsStartingResearch(true);
    setError('');
    try {
      await api.startResearch(campaign.id, locations.length ? { locations } : undefined);
      setShowLocationModal(false);
      setCampaign({ ...campaign, status: 'researching', started_at: new Date().toISOString() });
      setResearchActive(true);
      setAiMessage(
        locations.length
          ? `Research started - targeting: ${locations.join(', ')}`
          : 'Research started'
      );
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

  // Poll the review queue so AI background runs are visible in the UI.
  const pollReviewProgress = async (label: string) => {
    if (!campaign) return;
    const attempts = 15;
    let lastTotal = -1;
    for (let i = 0; i < attempts; i++) {
      await new Promise((resolve) => setTimeout(resolve, 4000));
      try {
        const response = await api.getLeads({
          campaign_id: campaign.id,
          status: 'review',
          per_page: 1,
        });
        lastTotal = response.data.total || 0;
        setAiMessage(`${label} running - ${lastTotal} lead${lastTotal === 1 ? '' : 's'} in review queue`);
      } catch {
        // transient poll errors are not worth surfacing
      }
    }
    fetchLeadsCount();
    fetchCampaign();
    setAiMessage(`${label} finished - ${Math.max(lastTotal, 0)} lead(s) in the review queue`);
  };

  const handleQualify = async () => {
    if (!campaign) return;
    setAiMessage('');
    setError('');
    try {
      const response = await api.qualifyCampaign(campaign.id);
      setAiMessage(`${response.data?.message || 'AI qualification started'} - checking progress...`);
      pollReviewProgress('AI qualification');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to start qualification';
      setError(message);
    }
  };

  const handleGenerateFollowups = async () => {
    if (!campaign) return;
    setAiMessage('');
    setError('');
    try {
      const response = await api.generateCampaignFollowups(campaign.id);
      setAiMessage(`${response.data?.message || 'Follow-up generation started'} - checking progress...`);
      pollReviewProgress('Follow-up generation');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to start follow-up generation';
      setError(message);
    }
  };

  const handleGenerateEmails = async () => {
    if (!campaign) return;
    setAiMessage('');
    setError('');
    try {
      const response = await api.generateCampaignEmails(campaign.id);
      setAiMessage(`${response.data?.message || 'Email generation started'} - checking progress...`);
      pollReviewProgress('Email generation');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to start email generation';
      setError(message);
    }
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

          <StageIndicator current={stageIndex} />

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

            <div className="flex flex-wrap justify-end gap-4 mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
              {campaign.status !== 'draft' && (
                <>
                  <button
                    onClick={handleQualify}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-md transition-colors"
                  >
                    🤖 Qualify with AI
                  </button>
                  <button
                    onClick={handleGenerateEmails}
                    className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded-md transition-colors"
                  >
                    ✉ Generate Emails
                  </button>
                  <button
                    onClick={handleGenerateFollowups}
                    className="bg-teal-600 hover:bg-teal-700 text-white px-6 py-2 rounded-md transition-colors"
                  >
                    ↻ Generate Follow-ups
                  </button>
                  <Link
                    href={`/leads/review?campaign_id=${campaign.id}`}
                    className="bg-yellow-600 hover:bg-yellow-700 text-white px-6 py-2 rounded-md transition-colors flex items-center gap-2"
                  >
                    Review Queue
                  </Link>
                  <Link
                    href={`/campaigns/${campaign.id}/approve`}
                    className="bg-blue-700 hover:bg-blue-800 text-white px-6 py-2 rounded-md transition-colors flex items-center gap-2"
                  >
                    📨 Review & Send
                  </Link>
                </>
              )}
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

          {aiMessage && (
            <div className="mt-6 p-4 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 text-indigo-800 dark:text-indigo-300 px-4 py-3 rounded-md text-sm">
              {aiMessage} - check the review queue or leads list in a minute.
            </div>
          )}

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
            {/* Location targeting modal */}
        {showLocationModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 shadow-xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                Target locations
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Where should we search for leads? Leave empty for worldwide results.
              </p>
              <input
                value={locationsInput}
                onChange={(e) => setLocationsInput(e.target.value)}
                placeholder="e.g. United States, United Kingdom"
                className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 mb-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              />
              <div className="flex flex-wrap gap-2 mb-5">
                {['United States', 'United Kingdom', 'Canada', 'Australia', 'Germany', 'India'].map(
                  (loc) => (
                    <button
                      key={loc}
                      onClick={() =>
                        setLocationsInput((prev) =>
                          prev
                            .split(',')
                            .map((l) => l.trim())
                            .filter(Boolean)
                            .includes(loc)
                            ? prev
                            : prev
                              ? `${prev}, ${loc}`
                              : loc
                        )
                      }
                      className="px-3 py-1 rounded-full text-xs bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/60"
                    >
                      + {loc}
                    </button>
                  )
                )}
              </div>
              <div className="flex justify-end gap-3 mt-4">
                <button
                  onClick={() => setShowLocationModal(false)}
                  className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmStartResearch}
                  disabled={isStartingResearch}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-5 py-2 rounded-md text-sm font-medium"
                >
                  {isStartingResearch ? 'Starting...' : 'Start Research'}
                </button>
              </div>
            </div>
          </div>
        )}
</main>
  );
}
