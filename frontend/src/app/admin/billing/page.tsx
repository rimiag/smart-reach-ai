'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import Skeleton from '@/components/Skeleton';
import type { AdminUser } from '@/types';

const PLANS = ['free', 'starter', 'pro'];
const BILLING_STATUSES = ['active', 'trial', 'past_due', 'cancelled'];

export default function AdminBillingPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingNotes, setEditingNotes] = useState<number | null>(null);
  const [notesDraft, setNotesDraft] = useState('');

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.getAdminUsers({ page: 1, per_page: 100 });
      setUsers(response.data.items);
      setError('');
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      setError(
        axiosError.response?.data?.error?.message ||
          axiosError.response?.data?.detail ||
          'Failed to load billing data'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const patch = async (u: AdminUser, fields: Record<string, unknown>) => {
    try {
      await api.updateAdminUser(u.id, fields);
      fetchUsers();
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      alert(
        axiosError.response?.data?.detail || axiosError.response?.data?.error?.message || 'Update failed'
      );
    }
  };

  const inputCls =
    'rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white';

  if (isLoading) return <Skeleton rows={4} />;

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/30 p-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead>
            <tr className="text-left text-xs uppercase text-gray-500 dark:text-gray-400">
              <th className="px-4 py-2.5">Client</th>
              <th className="px-4 py-2.5">Plan</th>
              <th className="px-4 py-2.5">Billing status</th>
              <th className="px-4 py-2.5">Usage (C/L/E)</th>
              <th className="px-4 py-2.5">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {users.map((u) => (
              <tr key={u.id} className={!u.is_active ? 'opacity-60' : ''}>
                <td className="px-4 py-2.5">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">{u.email}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    joined {new Date(u.created_at).toLocaleDateString()}
                  </div>
                </td>
                <td className="px-4 py-2.5">
                  <select
                    value={u.plan}
                    onChange={(e) => patch(u, { plan: e.target.value })}
                    className={inputCls}
                  >
                    {PLANS.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <select
                      value={u.billing_status}
                      onChange={(e) => patch(u, { billing_status: e.target.value })}
                      className={inputCls}
                    >
                      {BILLING_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <StatusBadge status={u.billing_status} />
                  </div>
                </td>
                <td className="px-4 py-2.5 text-sm text-gray-500 dark:text-gray-400">
                  {u.campaigns_count} / {u.leads_count} / {u.emails_count}
                </td>
                <td className="px-4 py-2.5 max-w-xs">
                  {editingNotes === u.id ? (
                    <div className="flex items-start gap-2">
                      <textarea
                        rows={2}
                        value={notesDraft}
                        onChange={(e) => setNotesDraft(e.target.value)}
                        className={`${inputCls} w-full`}
                      />
                      <div className="flex flex-col gap-1">
                        <button
                          onClick={() => { patch(u, { billing_notes: notesDraft }); setEditingNotes(null); }}
                          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingNotes(null)}
                          className="text-xs text-gray-500 hover:underline"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => { setEditingNotes(u.id); setNotesDraft(u.billing_notes || ''); }}
                      className="text-left text-sm text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400"
                      title="Click to edit notes"
                    >
                      {u.billing_notes || <span className="italic text-gray-400">- click to add -</span>}
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  No users yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500">
        Billing is informational (no payment gateway yet). Usage columns: Campaigns / Leads /
        Emails sent - computed live from platform data.
      </p>
    </div>
  );
}
