'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import type { Lead } from '@/types';

interface ManualEmailModalProps {
  lead: Lead;
  onClose: () => void;
  onSent: () => void;
}

/**
 * Compose and send an email to a single lead straight from the app.
 * The backend picks the sender identity (campaign sender or SMTP default),
 * appends the unsubscribe footer and logs the send to the mailbox.
 */
export default function ManualEmailModal({ lead, onClose, onSent }: ManualEmailModalProps) {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const handleSend = async () => {
    if (!subject.trim() || !body.trim()) return;
    setSending(true);
    setError('');
    try {
      await api.emailLead(lead.id, { subject: subject.trim(), body: body.trim() });
      onSent();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to send email');
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-lg bg-white dark:bg-gray-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            ✉ Email lead
          </h2>
          <button
            onClick={onClose}
            className="text-xl leading-none text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            ×
          </button>
        </div>

        <div className="space-y-4 px-5 py-4">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
              To
            </label>
            <div className="text-sm text-gray-900 dark:text-white">
              {lead.organization_name} &lt;{lead.email}&gt;
            </div>
          </div>

          <div>
            <label
              htmlFor="manual-email-subject"
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Subject *
            </label>
            <input
              id="manual-email-subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              maxLength={255}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Quick question about your team"
            />
          </div>

          <div>
            <label
              htmlFor="manual-email-body"
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Message *
            </label>
            <textarea
              id="manual-email-body"
              rows={8}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 whitespace-pre-wrap"
              placeholder={'Hi,\n\n...'}
            />
          </div>

          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-3 py-2 rounded-md text-sm">
              {error}
            </div>
          )}

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Sends immediately from your campaign sender address and includes an unsubscribe
            link. Their reply will land in your Mailbox.
          </p>
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
            disabled={sending || !subject.trim() || !body.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            {sending ? 'Sending...' : 'Send email'}
          </button>
        </div>
      </div>
    </div>
  );
}
