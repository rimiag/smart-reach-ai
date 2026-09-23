'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import type { MailboxMessage, MailboxThread, MailboxThreadDetail } from '@/types';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import Skeleton from '@/components/Skeleton';

function fmtTime(iso?: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  const mins = Math.floor((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return d.toLocaleDateString();
}

function MailboxContent() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [threads, setThreads] = useState<MailboxThread[]>([]);
  const [campaigns, setCampaigns] = useState<{ id: number; name: string }[]>([]);
  const [campaignFilter, setCampaignFilter] = useState('');
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [checkMessage, setCheckMessage] = useState('');
  const [isChecking, setIsChecking] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [thread, setThread] = useState<MailboxThreadDetail | null>(null);
  const [threadLoading, setThreadLoading] = useState(false);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState('');

  const fetchThreads = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = {};
      if (campaignFilter) params.campaign_id = Number(campaignFilter);
      if (unreadOnly) params.unread_only = true;
      const response = (await api.getMailboxThreads(params)).data as {
        items: MailboxThread[];
        total: number;
      };
      setThreads(response.items || []);
      setError('');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to load conversations');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, campaignFilter, unreadOnly]);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  // Campaign names for the filter select
  useEffect(() => {
    if (!isAuthenticated) return;
    api
      .getCampaigns({ per_page: 100 })
      .then((res) => {
        const data = res.data as { items?: { id: number; name: string }[] };
        setCampaigns((data.items || []).map((c) => ({ id: c.id, name: c.name })));
      })
      .catch(() => {});
  }, [isAuthenticated]);

  const openThread = async (leadId: number) => {
    setSelectedId(leadId);
    setThreadLoading(true);
    setSendError('');
    try {
      const response = (await api.getMailboxThread(leadId)).data as MailboxThreadDetail;
      setThread(response);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setSendError(axiosError.response?.data?.error?.message || 'Failed to load conversation');
    } finally {
      setThreadLoading(false);
    }
  };

  const handleSend = async () => {
    if (!thread || !draft.trim()) return;
    setSending(true);
    setSendError('');
    try {
      const response = (await api.sendMailboxReply({ lead_id: thread.lead_id, body: draft.trim() }))
        .data as { message: MailboxMessage };
      setThread({ ...thread, messages: [...thread.messages, response.message] });
      setDraft('');
      fetchThreads();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setSendError(axiosError.response?.data?.error?.message || 'Failed to send reply');
    } finally {
      setSending(false);
    }
  };

  const handleCheck = async () => {
    setIsChecking(true);
    setCheckMessage('');
    try {
      const summary = (await api.checkReplies()).data as {
        skipped?: string;
        matched?: number;
        unmatched?: number;
        by_category?: Record<string, number>;
      };
      if (summary.skipped) {
        setCheckMessage(`Mailbox check skipped: ${summary.skipped}`);
        return;
      }
      setCheckMessage(
        `Mailbox checked - ${summary.matched ?? 0} new repl${(summary.matched ?? 0) === 1 ? 'y' : 'ies'} matched, ${summary.unmatched ?? 0} not from a known lead.`
      );
      await fetchThreads();
      if (selectedId) openThread(selectedId);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setCheckMessage(axiosError.response?.data?.error?.message || 'Mailbox check failed');
    } finally {
      setIsChecking(false);
    }
  };

  if (authLoading) {
    return (
      <AppShell title="Mailbox">
        <Skeleton rows={4} />
      </AppShell>
    );
  }

  if (!isAuthenticated) {
    return (
      <AppShell title="Mailbox">
        <div className="text-center py-12 text-gray-600 dark:text-gray-300">
          Please{' '}
          <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">
            sign in
          </Link>{' '}
          to open your mailbox
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Mailbox"
      description="Conversations with your leads - outreach and replies in one thread"
      action={
        <div className="flex items-center gap-3">
          <button
            onClick={handleCheck}
            disabled={isChecking}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-md text-sm"
          >
            {isChecking ? 'Checking...' : 'Check mailbox now'}
          </button>
          <Link
            href="/campaigns"
            className="border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-md text-sm"
          >
            Campaigns
          </Link>
        </div>
      }
    >
      {checkMessage && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300 px-4 py-3 rounded-md mb-5 text-sm">
          {checkMessage}
        </div>
      )}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-5 text-sm">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-5">
        <select
          value={campaignFilter}
          onChange={(e) => setCampaignFilter(e.target.value)}
          className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white"
        >
          <option value="">All campaigns</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(e) => setUnreadOnly(e.target.checked)}
          />
          Unread only
        </label>
        <span className="ml-auto text-sm text-gray-500 dark:text-gray-400">
          {threads.length} conversation{threads.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        {/* Conversation list */}
        <div className={selectedId ? 'hidden lg:block' : 'block'}>
          {isLoading ? (
            <Skeleton rows={5} />
          ) : threads.length === 0 ? (
            <div className="border border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-8 text-center">
              <p className="text-gray-500 dark:text-gray-400 mb-1">No conversations yet.</p>
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Send a campaign, then check the mailbox for replies.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {threads.map((t) => (
                <button
                  key={t.lead_id}
                  onClick={() => openThread(t.lead_id)}
                  className={`w-full text-left p-4 rounded-lg border transition-colors ${
                    selectedId === t.lead_id
                      ? 'border-indigo-400 bg-indigo-50/60 dark:bg-indigo-900/20 dark:border-indigo-700'
                      : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-indigo-300 dark:hover:border-indigo-600'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                      {t.lead_name || t.email}
                    </span>
                    <span className="text-xs text-gray-400 shrink-0">{fmtTime(t.last_at)}</span>
                  </div>
                  {t.campaign_name && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {t.campaign_name}
                    </div>
                  )}
                  <p
                    className={`text-sm truncate mt-1 ${
                      t.unread_count > 0
                        ? 'text-gray-900 dark:text-gray-100 font-semibold'
                        : 'text-gray-500 dark:text-gray-400'
                    }`}
                  >
                    {t.last_direction === 'in' ? 'Received: ' : 'Sent: '}
                    {t.last_preview}
                  </p>
                  {t.unread_count > 0 && (
                    <span className="mt-2 inline-flex items-center rounded-full bg-blue-600 px-2 py-0.5 text-[11px] font-semibold text-white">
                      {t.unread_count} unread
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Thread + composer */}
        <div className={selectedId ? 'block' : 'hidden lg:block'}>
          {!selectedId ? (
            <div className="h-full min-h-[320px] flex items-center justify-center border border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-10 text-sm text-gray-400 dark:text-gray-500">
              Select a conversation to read and reply
            </div>
          ) : threadLoading ? (
            <Skeleton rows={4} />
          ) : thread ? (
            <div className="flex flex-col h-[calc(100vh-17rem)] min-h-[480px]">
              {/* Thread header */}
              <div className="flex items-center gap-3 border-b border-gray-200 dark:border-gray-700 pb-3">
                <button
                  onClick={() => setSelectedId(null)}
                  className="lg:hidden text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 text-lg"
                  aria-label="Back to conversations"
                >
                  &larr;
                </button>
                <div className="min-w-0">
                  <p className="font-semibold text-gray-900 dark:text-white truncate">
                    {thread.lead_name || thread.email}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {thread.email}
                    {thread.campaign_name ? ` - ${thread.campaign_name}` : ''}
                  </p>
                </div>
                <Link
                  href={`/leads/${thread.lead_id}`}
                  className="ml-auto text-sm text-blue-600 hover:text-blue-700 font-medium shrink-0"
                >
                  View lead &rarr;
                </Link>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto py-4 space-y-4">
                {thread.messages.map((m, i) => (
                  <div
                    key={i}
                    className={`flex ${m.direction === 'out' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${
                        m.direction === 'out'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200'
                      }`}
                    >
                      <div
                        className={`flex flex-wrap items-center gap-2 text-xs mb-1 ${
                          m.direction === 'out' ? 'text-indigo-200' : 'text-gray-400'
                        }`}
                      >
                        <span>{m.direction === 'out' ? `To: ${m.to_email}` : `From: ${m.from_email}`}</span>
                        {m.at && (
                          <>
                            <span>&middot;</span>
                            <span>{new Date(m.at).toLocaleString()}</span>
                          </>
                        )}
                      </div>
                      {m.subject && <p className="font-semibold mb-1">{m.subject}</p>}
                      {m.direction === 'in' && m.category && (
                        <p className="text-xs italic mb-1 opacity-80">
                          AI: {m.category.replace(/_/g, ' ')}
                          {m.ai_summary ? ` - ${m.ai_summary}` : ''}
                        </p>
                      )}
                      <p className="whitespace-pre-wrap">{m.body}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Composer */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
                {sendError && (
                  <p className="mb-2 text-sm text-red-600 dark:text-red-400">{sendError}</p>
                )}
                <textarea
                  rows={4}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Write your reply..."
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex justify-end mt-2">
                  <button
                    onClick={handleSend}
                    disabled={sending || !draft.trim()}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white px-5 py-2 rounded-md text-sm font-medium"
                  >
                    {sending ? 'Sending...' : 'Send reply'}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[320px] flex items-center justify-center text-sm text-gray-400">
              Conversation not found
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

export default function MailboxPage() {
  return <MailboxContent />;
}
