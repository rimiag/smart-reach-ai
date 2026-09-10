'use client';

import { Suspense, useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useSearchParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { Lead } from '@/types';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import Header from '@/components/Header';

interface LeadsResponse {
  items: Lead[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

function ReviewContent() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [campaignId, setCampaignId] = useState<number | null>(null);
  const [campaignName, setCampaignName] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [processingIds, setProcessingIds] = useState<number[]>([]);

  useEffect(() => {
    const param = searchParams.get('campaign_id');
    if (param) setCampaignId(Number(param));
  }, [searchParams]);

  const fetchLeads = async () => {
    if (!campaignId) return;
    try {
      const response: LeadsResponse = (await api.getLeads({ campaign_id: campaignId, per_page: 100 }))
        .data;
      // Review queue: highest scores first.
      setLeads(
        (response.items || []).sort((a, b) => b.lead_score - a.lead_score),
      );
      setError('');
      try {
        const campaignResponse = await api.getCampaign(campaignId);
        setCampaignName(campaignResponse.data.name);
      } catch {
        setCampaignName('Unknown Campaign');
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to load leads');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    fetchLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, campaignId]);

  const decide = async (lead: Lead, action: 'approve' | 'reject') => {
    setActionError('');
    setProcessingIds((prev) => [...prev, lead.id]);
    try {
      if (action === 'approve') {
        await api.approveLead(lead.id);
      } else {
        await api.rejectLead(lead.id);
      }
      await fetchLeads();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setActionError(axiosError.response?.data?.error?.message || `Failed to ${action} lead`);
    } finally {
      setProcessingIds((prev) => prev.filter((id) => id !== lead.id));
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-lime-600 dark:text-lime-400';
    if (score >= 40) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

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
          to review leads
        </div>
      </main>
    );
  }

  return (
    <AppShell>
      <Header
        title="Review Leads"
        description={campaignName ? `Campaign: ${campaignName}` : 'AI-qualified leads awaiting your decision'}
        action={
          <div className="flex gap-3">
            {campaignId && (
              <Link
                href={`/leads?campaign_id=${campaignId}`}
                className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
              >
                All Leads
              </Link>
            )}
            <Link
              href="/campaigns"
              className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
            >
              Campaigns
            </Link>
          </div>
        }
      />
      <div className="container mx-auto px-4 py-8">
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="text-center py-12">
            <div className="text-gray-600 dark:text-gray-400">Loading review queue...</div>
          </div>
        ) : !campaignId ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            No campaign selected - open this page from a campaign (Review Leads).
          </div>
        ) : leads.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-500 dark:text-gray-400 mb-4">
              No leads waiting for review.
            </div>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Leads appear here after AI qualification (or use &quot;Qualify with AI&quot; on the
              campaign page).
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {leads.map((lead) => {
              const isProcessing = processingIds.includes(lead.id);
              const isExpanded = expandedId === lead.id;
              return (
                <div
                  key={lead.id}
                  className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                          {lead.organization_name}
                        </h3>
                        {lead.email && (
                          <span className="text-sm text-gray-500 dark:text-gray-400">
                            {lead.email}
                          </span>
                        )}
                      </div>
                      {lead.ai_reasoning && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                          {lead.ai_reasoning}
                        </p>
                      )}
                      {lead.generated_email && (
                        <div className="mb-3">
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : lead.id)}
                            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                          >
                            {isExpanded ? 'Hide draft email' : 'Show draft email'}
                          </button>
                          {isExpanded && (
                            <pre className="mt-2 whitespace-pre-wrap bg-gray-50 dark:bg-gray-900/50 rounded-md p-3 text-sm text-gray-800 dark:text-gray-200">
                              {lead.generated_email}
                            </pre>
                          )}
                        </div>
                      )}
                      <div className="flex items-center gap-3 mt-3">
                        {lead.generated_email && (
                          <Link
                            href={`/leads/${lead.id}`}
                            className="text-sm text-purple-600 hover:text-purple-700 font-medium"
                          >
                            ✏ Edit draft
                          </Link>
                        )}
                        <Link
                          href={`/leads/${lead.id}`}
                          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                        >
                          View details →
                        </Link>
                      </div>
                    </div>

                    <div className="text-right ml-4 flex flex-col items-end gap-3">
                      <div>
                        <div className={`text-3xl font-bold ${getScoreColor(lead.lead_score)}`}>
                          {lead.lead_score}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Score</p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => decide(lead, 'approve')}
                          disabled={isProcessing}
                          className="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white px-4 py-2 rounded-md text-sm transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => decide(lead, 'reject')}
                          disabled={isProcessing}
                          className="bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white px-4 py-2 rounded-md text-sm transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {actionError && (
          <div className="fixed bottom-6 right-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md shadow-lg">
            {actionError}
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function LeadReviewPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-gray-50 dark:bg-gray-900" />}>
      <ReviewContent />
    </Suspense>
  );
}
