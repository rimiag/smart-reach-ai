'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import type { Lead } from '@/types';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import ExportButton from '@/components/ExportButton';
import StatusBadge from '@/components/StatusBadge';
import Skeleton from '@/components/Skeleton';
import EmptyState from '@/components/EmptyState';

interface LeadsResponse {
  items: Lead[];
  total: number;
}

type SortKey = 'score' | 'org' | 'date';

function LeadsContent() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [campaignId, setCampaignId] = useState<number | null>(null);
  const [campaignName, setCampaignName] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('date');

  // Read the campaign from the URL (?campaign_id=...)
  useEffect(() => {
    const campaignIdParam = searchParams.get('campaign_id');
    if (campaignIdParam) setCampaignId(Number(campaignIdParam));
  }, [searchParams]);

  const fetchLeads = useCallback(async () => {
    setIsLoading(true);
    if (!campaignId || !isAuthenticated) {
      setIsLoading(false);
      return;
    }
    try {
      const response: LeadsResponse = (await api.getLeads({ campaign_id: campaignId, per_page: 100 }))
        .data;
      setLeads(response.items || []);
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
  }, [campaignId, isAuthenticated]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  const sortedLeads = useMemo(() => {
    const copy = [...leads];
    if (sortKey === 'score') copy.sort((a, b) => b.lead_score - a.lead_score);
    if (sortKey === 'org')
      copy.sort((a, b) => a.organization_name.localeCompare(b.organization_name));
    if (sortKey === 'date')
      copy.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return copy;
  }, [leads, sortKey]);

  if (authLoading) {
    return (
      <AppShell title="Leads">
        <Skeleton rows={4} />
      </AppShell>
    );
  }

  if (!isAuthenticated) {
    return (
      <AppShell title="Leads">
        <EmptyState
          title="Sign in required"
          message="Sign in to view and manage your leads."
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
      title="Leads"
      description={campaignName ? `Campaign: ${campaignName}` : undefined}
      action={
        <div className="flex items-center gap-3">
          {campaignId && <ExportButton campaignId={campaignId} />}
          {campaignId && (
            <Link
              href={`/leads/new?campaign_id=${campaignId}`}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              + Add Lead
            </Link>
          )}
          {campaignId && (
            <Link
              href={`/campaigns/${campaignId}`}
              className="border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Campaign
            </Link>
          )}
        </div>
      }
    >
      {/* Status filter pills */}
      {campaignId && (
        <div className="flex flex-wrap items-center gap-2 mb-5">
          {['', 'new', 'review', 'approved', 'sent', 'interested', 'rejected'].map((s) => (
            <button
              key={s || 'all'}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                statusFilter === s
                  ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700'
              }`}
            >
              {s === '' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {isLoading ? (
        <Skeleton rows={5} />
      ) : !campaignId ? (
        <EmptyState
          title="No campaign selected"
          message="Pick a campaign to see its leads, or head to your campaigns list."
          action={
            <Link
              href="/campaigns"
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md text-sm font-medium"
            >
              Go to Campaigns
            </Link>
          }
        />
      ) : sortedLeads.length === 0 ? (
        <EmptyState
          title={statusFilter ? `No ${statusFilter} leads` : 'No leads yet'}
          message="Run research on the campaign to discover and qualify leads."
          action={
            !statusFilter ? (
              <Link
                href={`/campaigns/${campaignId}`}
                className="text-blue-600 hover:text-blue-700 font-medium text-sm"
              >
                Go to campaign →
              </Link>
            ) : undefined
          }
        />
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                <th className="px-4 py-3">
                  <button
                    onClick={() => setSortKey('org')}
                    className="hover:text-gray-900 dark:hover:text-white"
                  >
                    Organization
                  </button>
                </th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Keyword</th>
                <th className="px-4 py-3 text-right">
                  <button
                    onClick={() => setSortKey('score')}
                    className="hover:text-gray-900 dark:hover:text-white"
                  >
                    Score ↓
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button
                    onClick={() => setSortKey('date')}
                    className="hover:text-gray-900 dark:hover:text-white"
                  >
                    Date Found
                  </button>
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {sortedLeads.map((lead) => (
                <tr
                  key={lead.id}
                  className="border-b border-gray-100 dark:border-gray-700/60 hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/leads/${lead.id}`}
                      className="font-medium text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      {lead.organization_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={lead.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                    {lead.email ? (
                      <a href={`mailto:${lead.email}`} className="hover:text-blue-600">
                        {lead.email}
                      </a>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{lead.keyword}</td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-white">
                    {lead.lead_score}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/leads/${lead.id}`}
                      className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                    >
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<AppShell title="Leads"><span /></AppShell>}>
      <LeadsContent />
    </Suspense>
  );
}
