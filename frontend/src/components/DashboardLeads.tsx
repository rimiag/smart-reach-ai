'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { Campaign, Lead } from '@/types';
import StatusBadge from '@/components/StatusBadge';
import Skeleton from '@/components/Skeleton';
import EmptyState from '@/components/EmptyState';
import ExportButton from '@/components/ExportButton';
import LeadFormModal from '@/components/LeadFormModal';
import ManualEmailModal from '@/components/ManualEmailModal';

interface LeadsResponse {
  items: Lead[];
  total: number;
}

const STATUS_FILTERS = ['', 'new', 'review', 'approved', 'sent', 'interested', 'rejected'];

/**
 * The Dashboard "Leads" tab: every lead across campaigns with manual create,
 * campaign re-assignment and one-off manual emailing - no research needed.
 */
export default function DashboardLeads() {
  // /leads?campaign_id=N (links from campaign pages, leads/new redirect) preselects
  const searchParams = useSearchParams();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignFilter, setCampaignFilter] = useState(searchParams.get('campaign_id') ?? '');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editLead, setEditLead] = useState<Lead | null>(null);
  const [emailLeadTarget, setEmailLeadTarget] = useState<Lead | null>(null);

  const fetchLeads = useCallback(async () => {
    setIsLoading(true);
    try {
      const response: LeadsResponse = (
        await api.getLeads({
          per_page: 100,
          ...(campaignFilter ? { campaign_id: Number(campaignFilter) } : {}),
          ...(statusFilter ? { status: statusFilter } : {}),
        })
      ).data;
      setLeads(response.items || []);
      setError('');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to load leads');
    } finally {
      setIsLoading(false);
    }
  }, [campaignFilter, statusFilter]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Live URL sync: navigating to /leads?campaign_id=N re-applies the filter
  useEffect(() => {
    const campaignIdParam = searchParams.get('campaign_id');
    if (campaignIdParam) setCampaignFilter(campaignIdParam);
  }, [searchParams]);

  useEffect(() => {
    api
      .getCampaigns({ per_page: 100 })
      .then((res) => {
        const data = res.data as { items?: Campaign[] };
        setCampaigns(data.items || []);
      })
      .catch(() => {});
  }, []);

  const campaignName = (id: number) => campaigns.find((c) => c.id === id)?.name ?? `Campaign #${id}`;

  return (
    <div>
      {/* Toolbar: campaign filter + status pills + new lead */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <select
          value={campaignFilter}
          onChange={(e) => setCampaignFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300"
        >
          <option value="">All campaigns</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        <div className="flex flex-wrap items-center gap-2">
          {STATUS_FILTERS.map((s) => (
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

        <div className="ml-auto flex items-center gap-3">
          {campaignFilter && <ExportButton campaignId={Number(campaignFilter)} />}
          <button
            onClick={() => setShowCreate(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-md text-sm font-medium transition-colors"
          >
            + New Lead
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {isLoading ? (
        <Skeleton rows={5} />
      ) : leads.length === 0 ? (
        <EmptyState
          title={statusFilter ? `No ${statusFilter} leads` : 'No leads yet'}
          message="Create a lead manually, or run research on a campaign to discover leads."
          action={
            <button
              onClick={() => setShowCreate(true)}
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md text-sm font-medium"
            >
              + New Lead
            </button>
          }
        />
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                <th className="px-4 py-3">Organization</th>
                <th className="px-4 py-3">Campaign</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3 text-right">Score</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
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
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                    {campaignName(lead.campaign_id)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={lead.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                    {lead.email || <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-white">
                    {lead.lead_score}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      onClick={() => setEmailLeadTarget(lead)}
                      disabled={!lead.email}
                      title={lead.email ? 'Send an email to this lead' : 'This lead has no email address'}
                      className="text-blue-600 hover:text-blue-700 text-sm font-medium disabled:text-gray-400 disabled:cursor-not-allowed"
                    >
                      ✉ Email
                    </button>
                    <button
                      onClick={() => setEditLead(lead)}
                      className="ml-4 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white text-sm font-medium"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <LeadFormModal
          mode="create"
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            fetchLeads();
          }}
        />
      )}
      {editLead && (
        <LeadFormModal
          mode="edit"
          lead={editLead}
          onClose={() => setEditLead(null)}
          onSaved={() => {
            setEditLead(null);
            fetchLeads();
          }}
        />
      )}
      {emailLeadTarget && (
        <ManualEmailModal
          lead={emailLeadTarget}
          onClose={() => setEmailLeadTarget(null)}
          onSent={() => {
            setEmailLeadTarget(null);
            fetchLeads();
          }}
        />
      )}
    </div>
  );
}
