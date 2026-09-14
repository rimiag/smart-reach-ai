'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import StatsCards from '@/components/StatsCards';
import Skeleton from '@/components/Skeleton';
import type { OverviewStats } from '@/types';

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchOverview = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.getAdminOverview();
      setStats(response.data);
      setError('');
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      setError(
        axiosError.response?.data?.error?.message ||
          axiosError.response?.data?.detail ||
          'Failed to load overview'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  if (isLoading) return <Skeleton rows={4} />;

  if (error || !stats) {
    return (
      <div className="rounded-lg bg-red-50 dark:bg-red-900/30 p-4 text-sm text-red-700 dark:text-red-300">
        {error || 'No data'}
        <button onClick={fetchOverview} className="ml-3 underline">
          Retry
        </button>
      </div>
    );
  }

  const maxDay = Math.max(1, ...stats.emails_last_7_days.map((d) => d.count));

  return (
    <div className="space-y-6">
      <StatsCards
        stats={[
          { label: 'Users', value: stats.users_total },
          { label: 'Active users', value: stats.users_active },
          { label: 'Admins', value: stats.users_admins },
          { label: 'Campaigns', value: stats.campaigns_total },
          { label: 'Leads', value: stats.leads_total },
          { label: 'Emails sent', value: stats.emails_total },
          { label: 'Replies', value: stats.replies_total },
          { label: 'Suppressions', value: stats.suppressions_total },
        ]}
      />

      {/* Emails per day, last 7 days */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
          Emails sent - last 7 days
        </h2>
        <div className="flex items-end gap-3 h-36">
          {stats.emails_last_7_days.map((day) => (
            <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-xs text-gray-500 dark:text-gray-400">{day.count}</span>
              <div
                className="w-full rounded-t bg-indigo-500 dark:bg-indigo-400"
                style={{ height: `${(day.count / maxDay) * 100}%`, minHeight: '4px' }}
                title={`${day.date}: ${day.count}`}
              />
              <span className="text-[11px] text-gray-400 dark:text-gray-500">
                {day.date.slice(5)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent signups */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white px-5 py-4">
          Recent signups
        </h2>
        {stats.recent_signups.length === 0 ? (
          <p className="px-5 pb-5 text-sm text-gray-500 dark:text-gray-400">
            No users have registered yet.
          </p>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead>
              <tr className="text-left text-xs uppercase text-gray-500 dark:text-gray-400">
                <th className="px-5 py-2">Email</th>
                <th className="px-5 py-2">Name</th>
                <th className="px-5 py-2">Role</th>
                <th className="px-5 py-2">Registered</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {stats.recent_signups.map((u) => (
                <tr key={u.id}>
                  <td className="px-5 py-2.5 text-sm text-gray-900 dark:text-white">{u.email}</td>
                  <td className="px-5 py-2.5 text-sm text-gray-600 dark:text-gray-300">
                    {u.name || '-'}
                  </td>
                  <td className="px-5 py-2.5">
                    <StatusBadge status={u.role} />
                  </td>
                  <td className="px-5 py-2.5 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
