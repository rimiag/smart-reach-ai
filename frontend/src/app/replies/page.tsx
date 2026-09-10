'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import type { ReplyItem } from '@/types';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import Header from '@/components/Header';

interface RepliesResponse {
  items: ReplyItem[];
  total: number;
}

const CATEGORIES = [
  'all',
  'interested',
  'not_interested',
  'need_more_info',
  'request_meeting',
  'pricing_request',
  'out_of_office',
  'unsubscribe',
  'wrong_contact',
  'other',
];

function categoryBadge(category: string): string {
  const map: Record<string, string> = {
    interested: 'bg-green-100 text-green-800',
    request_meeting: 'bg-emerald-100 text-emerald-800',
    pricing_request: 'bg-lime-100 text-lime-800',
    need_more_info: 'bg-cyan-100 text-cyan-800',
    not_interested: 'bg-red-100 text-red-800',
    out_of_office: 'bg-gray-100 text-gray-700',
    unsubscribe: 'bg-pink-100 text-pink-800',
    wrong_contact: 'bg-orange-100 text-orange-800',
    other: 'bg-slate-100 text-slate-800',
  };
  return map[category] || 'bg-gray-100 text-gray-800';
}

function RepliesContent() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [replies, setReplies] = useState<ReplyItem[]>([]);
  const [total, setTotal] = useState(0);
  const [category, setCategory] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isChecking, setIsChecking] = useState(false);
  const [checkMessage, setCheckMessage] = useState('');
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const fetchReplies = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = { per_page: 100 };
      if (category !== 'all') params.category = category;
      const response: RepliesResponse = (await api.getReplies(params)).data;
      setReplies(response.items || []);
      setTotal(response.total || 0);
      setError('');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to load replies');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, category]);

  useEffect(() => {
    fetchReplies();
  }, [fetchReplies]);

  const handleCheck = async () => {
    setIsChecking(true);
    setCheckMessage('');
    try {
      const summary = (await api.checkReplies()).data;
      if (summary.skipped) {
        setCheckMessage(`Mailbox check skipped: ${summary.skipped}`);
        return;
      }
      const byCat = summary.by_category
        ? Object.entries(summary.by_category)
            .map(([cat, count]) => `${cat.replace('_', ' ')}: ${count}`)
            .join(', ')
        : '';
      setCheckMessage(
        `Mailbox checked - ${summary.matched ?? 0} new repl${(summary.matched ?? 0) === 1 ? 'y' : 'ies'} matched${
          byCat ? ` (${byCat})` : ''
        }, ${summary.unmatched ?? 0} not from a known lead.`
      );
      await fetchReplies();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setCheckMessage(axiosError.response?.data?.error?.message || 'Mailbox check failed');
    } finally {
      setIsChecking(false);
    }
  };

  const markRead = async (id: number) => {
    try {
      await api.markReplyRead(id);
      setReplies((prev) => prev.map((r) => (r.id === id ? { ...r, status: 'read' } : r)));
    } catch {
      setCheckMessage('Failed to mark reply as read');
    }
  };

  const toggleExpanded = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
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
          to view replies
        </div>
      </main>
    );
  }

  return (
    <AppShell>
      <Header
        title="Replies"
        description="Inbound replies from your outreach, classified by AI"
        action={
          <div className="flex items-center gap-3">
            <button
              onClick={handleCheck}
              disabled={isChecking}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-md text-sm"
            >
              {isChecking ? 'Checking...' : '✉ Check mailbox now'}
            </button>
            <Link
              href="/campaigns"
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md transition-colors text-sm"
            >
              Campaigns
            </Link>
          </div>
        }
      />
      <div className="container mx-auto px-4 py-8">
        {/* Category filter */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                category === cat
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700'
              }`}
            >
              {cat === 'all' ? 'All' : cat.replace('_', ' ')}
            </button>
          ))}
          <span className="ml-auto text-sm text-gray-500 dark:text-gray-400">
            {total} repl{total === 1 ? 'y' : 'ies'}
          </span>
        </div>

        {checkMessage && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300 px-4 py-3 rounded-md mb-6 text-sm">
            {checkMessage}
          </div>
        )}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="text-center py-12 text-gray-600 dark:text-gray-400">Loading replies...</div>
        ) : replies.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400 mb-2">
              No replies{category !== 'all' ? ` in "${category}"` : ''}.
            </p>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Use "Check mailbox now" to poll your inbox, or wait for the periodic check.
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {replies.map((reply) => {
              const isExpanded = expandedIds.has(reply.id);
              const isLong = reply.body.length > 300;
              return (
                <div
                  key={reply.id}
                  className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 ${
                    reply.status === 'unread' ? 'border-l-4 border-blue-500' : ''
                  }`}
                >
                  <div className="flex justify-between items-start mb-2 gap-3 flex-wrap">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${categoryBadge(
                          reply.category
                        )}`}
                      >
                        {reply.category.replace('_', ' ')}
                      </span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {reply.from_name || reply.from_email}
                      </span>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {reply.from_email}
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {reply.received_at ? new Date(reply.received_at).toLocaleString() : ''}
                    </span>
                  </div>

                  {reply.subject && (
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-1">
                      {reply.subject}
                    </p>
                  )}
                  {reply.ai_summary && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2 italic">
                      {reply.ai_summary}
                    </p>
                  )}
                  <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {isLong && !isExpanded ? `${reply.body.slice(0, 300)}... ` : reply.body}
                    {isLong && (
                      <button
                        onClick={() => toggleExpanded(reply.id)}
                        className="text-blue-600 hover:text-blue-700 text-sm ml-1"
                      >
                        {isExpanded ? 'show less' : 'show more'}
                      </button>
                    )}
                  </p>

                  <div className="flex items-center gap-3 mt-3">
                    {reply.status === 'unread' && (
                      <button
                        onClick={() => markRead(reply.id)}
                        className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                      >
                        Mark as read
                      </button>
                    )}
                    <Link
                      href={`/leads/${reply.lead_id}`}
                      className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400"
                    >
                      View lead →
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function RepliesPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-gray-50 dark:bg-gray-900" />}>
      <RepliesContent />
    </Suspense>
  );
}
