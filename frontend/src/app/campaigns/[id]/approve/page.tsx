'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import type { Campaign, Lead } from '@/types';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import Header from '@/components/Header';

interface LeadsResponse {
  items: Lead[];
  total: number;
}

export default function ApproveCampaignPage() {
  const { id } = useParams();
  const campaignId = Number(id);
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [reviewCount, setReviewCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [progressMessage, setProgressMessage] = useState('');

  // Sender identity (prefilled from the last send)
  const [senderName, setSenderName] = useState('');
  const [senderCompany, setSenderCompany] = useState('');
  const [fromEmail, setFromEmail] = useState('');
  const [replyTo, setReplyTo] = useState('');

  const fetchAll = useCallback(async () => {
    try {
      const campaignResponse = await api.getCampaign(campaignId);
      const data: Campaign = campaignResponse.data;
      setCampaign(data);

      const settings = (data.settings || {}) as Record<string, string>;
      setSenderName((prev) => prev || settings.sender_name || '');
      setSenderCompany((prev) => prev || settings.sender_company || '');
      setFromEmail((prev) => prev || settings.from_email || '');
      setReplyTo((prev) => prev || settings.reply_to || '');

      const leadsResponse: LeadsResponse = (
        await api.getLeads({ campaign_id: campaignId, status: 'approved', per_page: 100 })
      ).data;
      setLeads((leadsResponse.items || []).filter((l) => l.generated_email));

      const reviewResponse: LeadsResponse = (
        await api.getLeads({ campaign_id: campaignId, status: 'review', per_page: 1 })
      ).data;
      setReviewCount(reviewResponse.total || 0);
      setError('');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to load campaign');
    } finally {
      setIsLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    if (!isAuthenticated || !campaignId) return;
    fetchAll();
  }, [isAuthenticated, campaignId, fetchAll]);

  const handleApproveAll = async () => {
    setError('');
    try {
      const response = await api.approveAllLeads(campaignId);
      setProgressMessage(response.data?.message || 'Leads approved');
      await fetchAll();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to approve leads');
    }
  };

  const handleSend = async () => {
    if (!campaign || !confirmChecked) return;
    setIsSending(true);
    setProgressMessage('');
    setError('');
    try {
      const response = await api.sendCampaignEmails(campaignId, {
        sender_name: senderName,
        sender_company: senderCompany,
        from_email: fromEmail,
        reply_to: replyTo || undefined,
      });
      setProgressMessage(`${response.data?.message || 'Sending started'} - sending in progress...`);

      // Poll send progress via campaign stats (emails_sent counter).
      const startSent = campaign ? 0 : 0;
      let lastSent = startSent;
      for (let i = 0; i < 30; i++) {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        const statsResponse = await api.getCampaignStats(campaignId);
        lastSent = statsResponse.data.emails_sent || 0;
        setProgressMessage(`Sending in progress - ${lastSent} email(s) sent so far`);
      }
      await fetchAll();
      setProgressMessage(`Send run finished - ${lastSent} email(s) sent in total. `);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to start sending');
    } finally {
      setIsSending(false);
    }
  };

  if (authLoading || isLoading) {
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
          to review sends
        </div>
      </main>
    );
  }

  return (
    <AppShell>
      <Header
        title="Review & Send"
        description={campaign ? `Campaign: ${campaign.name}` : undefined}
        action={
          <Link
            href={`/campaigns/${campaignId}`}
            className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
          >
            ← Back to Campaign
          </Link>
        }
      />
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {/* Step 1: drafts in review */}
        {reviewCount > 0 && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4 mb-6 flex items-center justify-between">
            <p className="text-sm text-yellow-800 dark:text-yellow-300">
              {reviewCount} reviewed lead{reviewCount === 1 ? '' : 's'} still need email drafts.
            </p>
            <button
              onClick={handleApproveAll}
              className="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded-md text-sm"
            >
              Approve all with drafts
            </button>
          </div>
        )}

        {/* Step 2: sender identity */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Sender identity
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">
                Your name *
              </label>
              <input
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                placeholder="e.g. Rizwan Ahmed"
                className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">
                Your company
              </label>
              <input
                value={senderCompany}
                onChange={(e) => setSenderCompany(e.target.value)}
                placeholder="e.g. Acme Consulting"
                className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">
                From email (SMTP account) *
              </label>
              <input
                type="email"
                value={fromEmail}
                onChange={(e) => setFromEmail(e.target.value)}
                placeholder="you@yourcompany.com"
                className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1">
                Reply-To (optional)
              </label>
              <input
                type="email"
                value={replyTo}
                onChange={(e) => setReplyTo(e.target.value)}
                placeholder="same as From if empty"
                className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              />
            </div>
          </div>
          <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">
            Every email automatically gets a working unsubscribe link (compliance).
          </p>
        </div>

        {/* Step 3: queue */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Ready to send ({leads.length})
            </h2>
            {reviewCount > 0 && (
              <Link
                href={`/leads/review?campaign_id=${campaignId}`}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Review {reviewCount} draftless lead{reviewCount === 1 ? '' : 's'} →
              </Link>
            )}
          </div>

          {leads.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No approved leads with email drafts yet. Approve leads in the review queue first.
            </p>
          ) : (
            <div className="space-y-3">
              {leads.map((lead) => (
                <div
                  key={lead.id}
                  className="flex justify-between items-center bg-gray-50 dark:bg-gray-900/50 rounded-md p-3"
                >
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {lead.organization_name}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{lead.email}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <Link
                      href={`/leads/${lead.id}`}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      ✏ Edit draft
                    </Link>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">
                        {lead.lead_score}
                      </p>
                      <p className="text-xs text-gray-400">score</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Step 4: send */}
        {progressMessage && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300 px-4 py-3 rounded-md mb-6 text-sm">
            {progressMessage}
          </div>
        )}

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <label className="flex items-start gap-3 mb-4">
            <input
              type="checkbox"
              checked={confirmChecked}
              onChange={(e) => setConfirmChecked(e.target.checked)}
              className="mt-1"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              I have reviewed these {leads.length} email draft
              {leads.length === 1 ? '' : 's'} and approve sending them from {fromEmail || 'my address'}.
              Sending respects daily/hourly limits and pauses automatically.
            </span>
          </label>
          <button
            onClick={handleSend}
            disabled={!confirmChecked || isSending || leads.length === 0 || !fromEmail || !senderName}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 dark:disabled:bg-blue-900 text-white px-6 py-3 rounded-md transition-colors font-medium"
          >
            {isSending ? 'Sending...' : `Start sending ${leads.length} email${leads.length === 1 ? '' : 's'}`}
          </button>
        </div>
      </div>
    </AppShell>
  );
}
