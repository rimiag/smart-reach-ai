'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useSearchParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { Lead } from '@/types';
import Link from 'next/link';
import Header from '@/components/Header';

interface LeadsResponse {
  items: Lead[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export default function LeadsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [campaignId, setCampaignId] = useState<number | null>(null);
  const [campaignName, setCampaignName] = useState<string>('');

  useEffect(() => {
    // Get campaign_id from URL parameters
    const campaignIdParam = searchParams.get('campaign_id');
    if (campaignIdParam) {
      setCampaignId(Number(campaignIdParam));
    }
  }, [searchParams]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchLeads = async () => {
      if (!campaignId) return;

      try {
        setIsLoading(true);
        const response = await api.getLeads({ campaign_id: campaignId });
        setLeads(response.data.items || []);
        setError('');

        // Also fetch campaign name
        try {
          const campaignResponse = await api.getCampaign(campaignId);
          setCampaignName(campaignResponse.data.name);
        } catch {
          setCampaignName('Unknown Campaign');
        }
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
        const message = axiosError.response?.data?.error?.message || 'Failed to load leads';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchLeads();
  }, [isAuthenticated, campaignId]);

  if (authLoading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-300">Loading...</div>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-300">
          Please <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">sign in</Link> to view leads
        </div>
      </main>
    );
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      new: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
      researching: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
      qualified: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
      review: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300',
      approved: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-300',
      rejected: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
      scheduled: 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
      sent: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-300',
      replied: 'bg-teal-100 dark:bg-teal-900/30 text-teal-800 dark:text-teal-300',
      interested: 'bg-lime-100 dark:bg-lime-900/30 text-lime-800 dark:text-lime-300',
      not_interested: 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300',
      unsubscribed: 'bg-pink-100 dark:bg-pink-900/30 text-pink-800 dark:text-pink-300',
      bounced: 'bg-rose-100 dark:bg-rose-900/30 text-rose-800 dark:text-rose-300',
      do_not_contact: 'bg-zinc-100 dark:bg-zinc-900/30 text-zinc-800 dark:text-zinc-300',
    };
    return colors[status] || 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300';
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
    if (score >= 40) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header
        title="Leads"
        description={campaignName ? `Campaign: ${campaignName}` : undefined}
        action={
          <div className="flex gap-3">
            {campaignId && (
              <Link
                href={`/campaigns/${campaignId}`}
                className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
              >
                ← Back to Campaign
              </Link>
            )}
            <Link
              href="/campaigns"
              className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
            >
              All Campaigns
            </Link>
          </div>
        }
      />
      <div className="container mx-auto px-4 py-8">

        {campaignId ? (
          <>
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
                {error}
              </div>
            )}

            {isLoading ? (
            <div className="text-center py-12">
              <div className="text-gray-600 dark:text-gray-400">Loading leads...</div>
            </div>
          ) : leads.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-500 dark:text-gray-400 mb-4">
                No leads found for this campaign
              </div>
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Start research to discover leads
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {leads.map((lead) => (
                <div
                  key={lead.id}
                  className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                          {lead.organization_name}
                        </h3>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(lead.status)}`}>
                          {lead.status.charAt(0).toUpperCase() + lead.status.slice(1).replace('_', ' ')}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                        {lead.contact_name && (
                          <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">Contact</p>
                            <p className="text-gray-900 dark:text-white">{lead.contact_name}</p>
                          </div>
                        )}
                        {lead.job_title && (
                          <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">Title</p>
                            <p className="text-gray-900 dark:text-white">{lead.job_title}</p>
                          </div>
                        )}
                        {lead.email && (
                          <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">Email</p>
                            <p className="text-gray-900 dark:text-white">
                              <a href={`mailto:${lead.email}`} className="text-blue-600 hover:text-blue-700">
                                {lead.email}
                              </a>
                            </p>
                          </div>
                        )}
                        {lead.website && (
                          <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">Website</p>
                            <a href={lead.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-700">
                              {lead.website}
                            </a>
                          </div>
                        )}
                      </div>

                      {lead.ai_reasoning && (
                        <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            <span className="font-medium">AI Reasoning:</span> {lead.ai_reasoning}
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="text-right ml-4">
                      <div className={`text-3xl font-bold ${getScoreColor(lead.lead_score)}`}>
                        {lead.lead_score}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Score</p>
                      <Link
                        href={`/leads/${lead.id}`}
                        className="mt-3 inline-block text-blue-600 hover:text-blue-700 font-medium text-sm"
                      >
                        View Details →
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          </>
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-500 dark:text-gray-400 mb-4">
              No campaign selected
            </div>
            <Link
              href="/campaigns"
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              Go to Campaigns →
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
