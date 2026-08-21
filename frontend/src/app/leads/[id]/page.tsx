'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import type { Lead } from '@/types';
import Link from 'next/link';
import Header from '@/components/Header';

export default function LeadDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [lead, setLead] = useState<Lead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !id) return;

    const fetchLead = async () => {
      try {
        setIsLoading(true);
        const response = await api.getLead(Number(id));
        setLead(response.data);
        setError('');
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
        const message = axiosError.response?.data?.error?.message || 'Failed to load lead';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchLead();
  }, [isAuthenticated, id]);

  const handleApprove = async () => {
    if (!lead) return;

    try {
      setIsProcessing(true);
      await api.approveLead(lead.id);
      // Update lead status locally
      setLead({ ...lead, status: 'approved', approved_at: new Date().toISOString() });
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to approve lead';
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!lead) return;

    try {
      setIsProcessing(true);
      await api.rejectLead(lead.id);
      // Update lead status locally
      setLead({ ...lead, status: 'rejected' });
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to reject lead';
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDelete = async () => {
    if (!lead) return;

    if (!confirm('Are you sure you want to delete this lead?')) {
      return;
    }

    try {
      setIsProcessing(true);
      await api.deleteLead(lead.id);
      router.push('/campaigns');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to delete lead';
      setError(message);
      setIsProcessing(false);
    }
  };

  if (authLoading || isLoading) {
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

  if (error && !lead) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md">
            {error}
          </div>
          <Link href="/campaigns" className="mt-4 inline-block text-blue-600 hover:text-blue-700">
            ← Back to Campaigns
          </Link>
        </div>
      </main>
    );
  }

  if (!lead) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="container mx-auto px-4 py-8">
          <div className="text-gray-500 dark:text-gray-400">Lead not found</div>
          <Link href="/campaigns" className="mt-4 inline-block text-blue-600 hover:text-blue-700">
            ← Back to Campaigns
          </Link>
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
    if (score >= 80) return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
    if (score >= 40) return 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20';
    return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
  };

  const canApprove = ['new', 'qualified', 'review'].includes(lead.status);
  const canReject = ['new', 'qualified', 'review'].includes(lead.status);

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header
        title="Lead Details"
        description={`Organization: ${lead.organization_name}`}
        action={
          <Link
            href={`/campaigns/${lead.campaign_id}`}
            className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
          >
            ← Back to Campaign
          </Link>
        }
      />
      <div className="container mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <div className="mb-6 text-sm">
          <Link href="/campaigns" className="text-blue-600 hover:text-blue-700">
            Campaigns
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <Link href={`/campaigns/${lead.campaign_id}`} className="text-blue-600 hover:text-blue-700">
            Campaign #{lead.campaign_id}
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <span className="text-gray-600 dark:text-gray-400">Lead #{lead.id}</span>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                {lead.organization_name}
              </h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(lead.status)}`}>
                {lead.status.charAt(0).toUpperCase() + lead.status.slice(1).replace('_', ' ')}
              </span>
            </div>
            {lead.keyword && (
              <p className="text-gray-600 dark:text-gray-400">
                Found via: <span className="font-medium">{lead.keyword}</span>
              </p>
            )}
          </div>

          {/* Lead Score Card */}
          <div className={`px-6 py-4 rounded-lg ${getScoreColor(lead.lead_score)}`}>
            <div className="text-4xl font-bold">{lead.lead_score}</div>
            <div className="text-sm mt-1">Lead Score</div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 mb-6">
          {canApprove && (
            <button
              onClick={handleApprove}
              disabled={isProcessing}
              className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? 'Processing...' : '✓ Approve'}
            </button>
          )}
          {canReject && (
            <button
              onClick={handleReject}
              disabled={isProcessing}
              className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? 'Processing...' : '✗ Reject'}
            </button>
          )}
          <Link
            href={`/campaigns/${lead.campaign_id}`}
            className="px-6 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md transition-colors"
          >
            ← Back to Campaign
          </Link>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Contact Information */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Contact Information
            </h2>
            <div className="space-y-3">
              {lead.contact_name && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Contact Name</p>
                  <p className="text-gray-900 dark:text-white">{lead.contact_name}</p>
                </div>
              )}
              {lead.job_title && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Job Title</p>
                  <p className="text-gray-900 dark:text-white">{lead.job_title}</p>
                </div>
              )}
              {lead.department && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Department</p>
                  <p className="text-gray-900 dark:text-white">{lead.department}</p>
                </div>
              )}
              {lead.email && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Email</p>
                  <a
                    href={`mailto:${lead.email}`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    {lead.email}
                  </a>
                </div>
              )}
              {lead.phone && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Phone</p>
                  <a
                    href={`tel:${lead.phone}`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    {lead.phone}
                  </a>
                </div>
              )}
              {(lead.city || lead.country) && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Location</p>
                  <p className="text-gray-900 dark:text-white">
                    {[lead.city, lead.country].filter(Boolean).join(', ')}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Organization & Source */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Organization & Source
            </h2>
            <div className="space-y-3">
              {lead.website && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Website</p>
                  <a
                    href={lead.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700"
                  >
                    {lead.website}
                  </a>
                </div>
              )}
              {lead.contact_page_url && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Contact Page</p>
                  <a
                    href={lead.contact_page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700"
                  >
                    {lead.contact_page_url}
                  </a>
                </div>
              )}
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Source URL</p>
                <a
                  href={lead.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-700 text-sm break-all"
                >
                  {lead.source_url}
                </a>
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Discovered</p>
                <p className="text-gray-900 dark:text-white">
                  {new Date(lead.discovered_at).toLocaleDateString()}
                </p>
              </div>
              {lead.qualified_at && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Qualified</p>
                  <p className="text-gray-900 dark:text-white">
                    {new Date(lead.qualified_at).toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* AI Qualification */}
          {lead.ai_reasoning && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                AI Qualification
              </h2>
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                <p className="text-gray-700 dark:text-gray-300">
                  {lead.ai_reasoning}
                </p>
              </div>
              {lead.ai_research_summary && (
                <div className="mt-4">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Research Summary</p>
                  <p className="text-gray-700 dark:text-gray-300 text-sm">
                    {lead.ai_research_summary}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Tracking & Notes */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Tracking Information
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Emails Sent</span>
                <span className="font-medium text-gray-900 dark:text-white">{lead.emails_sent}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Messages Sent</span>
                <span className="font-medium text-gray-900 dark:text-white">{lead.messages_sent}</span>
              </div>
              {lead.last_contacted_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Last Contacted</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {new Date(lead.last_contacted_at).toLocaleDateString()}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Do Not Contact</span>
                <span className={`font-medium ${lead.do_not_contact ? 'text-red-600' : 'text-green-600'}`}>
                  {lead.do_not_contact ? 'Yes' : 'No'}
                </span>
              </div>
              {lead.unsubscribed_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Unsubscribed</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {new Date(lead.unsubscribed_at).toLocaleDateString()}
                  </span>
                </div>
              )}
              {lead.notes && (
                <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Notes</p>
                  <p className="text-gray-700 dark:text-gray-300 text-sm">{lead.notes}</p>
                </div>
              )}
            </div>

            {/* Danger Zone */}
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={handleDelete}
                disabled={isProcessing}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Delete Lead
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
