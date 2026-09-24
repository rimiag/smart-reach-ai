'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { Campaign, Lead } from '@/types';

interface ComposeModalProps {
  onClose: () => void;
  /** Called with the lead the email was sent to (thread now exists) */
  onSent: (leadId: number) => void;
}

/**
 * Start a NEW conversation from the Mailbox: pick an existing lead, or type a
 * fresh address - which auto-creates a lead (filed under the chosen campaign)
 * so the email stays tracked and the thread appears in the mailbox.
 */
export default function ComposeModal({ onClose, onSent }: ComposeModalProps) {
  const [mode, setMode] = useState<'lead' | 'new'>('lead');
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [campaignFilter, setCampaignFilter] = useState('');
  const [selectedLeadId, setSelectedLeadId] = useState(0);
  const [newEmail, setNewEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.getCampaigns({ per_page: 100 }),
      api.getLeads({ per_page: 100 }),
    ])
      .then(([campaignsRes, leadsRes]) => {
        if (cancelled) return;
        setCampaigns((campaignsRes.data as { items?: Campaign[] }).items || []);
        setLeads((leadsRes.data as { items?: Lead[] }).items || []);
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load campaigns or leads');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Lead picker filtered by the optional campaign selection
  const visibleLeads = useMemo(
    () =>
      campaignFilter
        ? leads.filter((l) => l.campaign_id === Number(campaignFilter))
        : leads,
    [leads, campaignFilter]
  );

  // In "new address" mode: does the typed email already exist as a lead?
  const matchedLead = useMemo(() => {
    const needle = newEmail.trim().toLowerCase();
    if (!needle) return null;
    return (
      leads.find((l) => (l.email || '').toLowerCase() === needle) ?? null
    );
  }, [leads, newEmail]);

  const canSend =
    subject.trim() !== '' &&
    body.trim() !== '' &&
    (mode === 'lead' ? selectedLeadId > 0 : Boolean(matchedLead) || campaignFilter !== '');

  const handleSend = async () => {
    if (!canSend || sending) return;
    setSending(true);
    setError('');
    try {
      let lead: Lead | undefined;
      if (mode === 'lead') {
        lead = leads.find((l) => l.id === selectedLeadId);
      } else if (matchedLead) {
        lead = matchedLead;
      } else {
        // Fresh address: create the lead first so the email is tracked.
        const domain = newEmail.trim().split('@')[1] || 'unknown';
        const website = `https://${domain}`;
        const response = await api.createLead({
          campaign_id: Number(campaignFilter),
          organization_name: domain,
          website,
          email: newEmail.trim(),
          keyword: 'manual',
          source_url: website,
        });
        lead = response.data as Lead;
      }
      if (!lead) {
        setError('Pick a recipient first');
        setSending(false);
        return;
      }
      try {
        await api.emailLead(lead.id, { subject: subject.trim(), body: body.trim() });
        onSent(lead.id);
      } catch (sendErr: unknown) {
        const axiosError = sendErr as { response?: { data?: { error?: { message?: string } } } };
        const detail = axiosError.response?.data?.error?.message || 'Failed to send email';
        setError(
          mode === 'new' && !matchedLead
            ? `${detail} (the lead was added to your Leads tab - you can retry from there)`
            : detail
        );
        setSending(false);
        return;
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to send email');
      setSending(false);
    }
  };

  const inputClass =
    'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-lg bg-white dark:bg-gray-800 shadow-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">✉ Compose</h2>
          <button
            onClick={onClose}
            className="text-xl leading-none text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            ×
          </button>
        </div>

        <div className="space-y-4 px-5 py-4">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-3 py-2 rounded-md text-sm">
              {error}
            </div>
          )}

          {/* Recipient mode toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => setMode('lead')}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                mode === 'lead'
                  ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
              }`}
            >
              Pick a lead
            </button>
            <button
              onClick={() => setMode('new')}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                mode === 'new'
                  ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
              }`}
            >
              New address
            </button>
          </div>

          {loading ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading...</p>
          ) : (
            <>
              <div>
                <label htmlFor="compose-campaign" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Campaign {mode === 'new' && !matchedLead ? '*' : '(optional filter)'}
                </label>
                <select
                  id="compose-campaign"
                  value={campaignFilter}
                  onChange={(e) => setCampaignFilter(e.target.value)}
                  className={inputClass}
                >
                  <option value="">All campaigns</option>
                  {campaigns.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              {mode === 'lead' ? (
                <div>
                  <label htmlFor="compose-lead" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Lead *
                  </label>
                  <select
                    id="compose-lead"
                    value={selectedLeadId || ''}
                    onChange={(e) => setSelectedLeadId(Number(e.target.value))}
                    className={inputClass}
                  >
                    <option value="">Select a lead</option>
                    {visibleLeads.map((l) => (
                      <option key={l.id} value={l.id} disabled={!l.email}>
                        {l.organization_name}
                        {l.email ? ` - ${l.email}` : ' (no email)'}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div>
                  <label htmlFor="compose-email" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    To *
                  </label>
                  <input
                    id="compose-email"
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    className={inputClass}
                    placeholder="contact@example.com"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {matchedLead
                      ? `This address is already a lead: ${matchedLead.organization_name}.`
                      : 'Not a lead yet - one will be created (pick a campaign above) so the conversation stays in your mailbox.'}
                  </p>
                </div>
              )}

              <div>
                <label htmlFor="compose-subject" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Subject *
                </label>
                <input
                  id="compose-subject"
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  maxLength={255}
                  className={inputClass}
                  placeholder="Introduction from ReachPulse"
                />
              </div>

              <div>
                <label htmlFor="compose-body" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Message *
                </label>
                <textarea
                  id="compose-body"
                  rows={7}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className={`${inputClass} whitespace-pre-wrap`}
                  placeholder={'Hi,\n\n...'}
                />
              </div>

              <p className="text-xs text-gray-500 dark:text-gray-400">
                Sends immediately from your campaign sender address (or SMTP default) and
                includes an unsubscribe link. Replies will appear in this mailbox.
              </p>
            </>
          )}
        </div>

        <div className="flex justify-end gap-3 border-t border-gray-200 dark:border-gray-700 px-5 py-4">
          <button
            onClick={onClose}
            className="border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSend}
            disabled={sending || loading || !canSend}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
