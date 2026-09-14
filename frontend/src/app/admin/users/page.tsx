'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import Skeleton from '@/components/Skeleton';
import { useAuth } from '@/hooks/useAuth';
import type { AdminUser } from '@/types';

const PLANS = ['free', 'starter', 'pro'];
const BILLING_STATUSES = ['active', 'trial', 'past_due', 'cancelled'];

interface EditForm {
  name: string;
  role: 'admin' | 'user';
  is_active: boolean;
  password: string;
  plan: string;
  billing_status: string;
  billing_notes: string;
}

function toForm(u: AdminUser): EditForm {
  return {
    name: u.name || '',
    role: u.role,
    is_active: u.is_active,
    password: '',
    plan: u.plan,
    billing_status: u.billing_status,
    billing_notes: u.billing_notes || '',
  };
}

export default function AdminUsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const perPage = 25;

  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    email: '',
    name: '',
    password: '',
    role: 'user' as 'admin' | 'user',
  });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);

  // Debounce the search box
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, unknown> = { page, per_page: perPage };
      if (search) params.search = search;
      if (roleFilter) params.role = roleFilter;
      if (statusFilter) params.is_active = statusFilter === 'active';
      const response = await api.getAdminUsers(params);
      setUsers(response.data.items);
      setTotal(response.data.total);
      setPages(Math.max(1, Math.ceil(response.data.total / perPage)));
      setError('');
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      setError(
        axiosError.response?.data?.error?.message ||
          axiosError.response?.data?.detail ||
          'Failed to load users'
      );
    } finally {
      setIsLoading(false);
    }
  }, [page, search, roleFilter, statusFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const saveEdit = async (u: AdminUser) => {
    if (!editForm) return;
    const payload: Record<string, unknown> = {
      name: editForm.name || null,
      role: editForm.role,
      is_active: editForm.is_active,
      plan: editForm.plan,
      billing_status: editForm.billing_status,
      billing_notes: editForm.billing_notes || null,
    };
    if (editForm.password) payload.password = editForm.password;
    try {
      await api.updateAdminUser(u.id, payload);
      setEditingId(null);
      setEditForm(null);
      fetchUsers();
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      setError(
        axiosError.response?.data?.error?.message ||
          axiosError.response?.data?.detail ||
          'Update failed'
      );
    }
  };

  const toggleActive = async (u: AdminUser) => {
    const verb = u.is_active ? 'deactivate' : 'reactivate';
    if (!confirm(`Are you sure you want to ${verb} ${u.email}?`)) return;
    try {
      await api.updateAdminUser(u.id, { is_active: !u.is_active });
      fetchUsers();
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      alert(axiosError.response?.data?.detail || axiosError.response?.data?.error?.message || 'Failed');
    }
  };

  const deleteUser = async (u: AdminUser) => {
    const msg =
      `Delete ${u.email} permanently?\n\n` +
      `This also removes ${u.campaigns_count} campaign(s), ${u.leads_count} lead(s) and ` +
      `${u.emails_count} email record(s). This cannot be undone.`;
    if (!confirm(msg)) return;
    const typed = prompt(`Type the email (${u.email}) to confirm deletion:`);
    if (typed !== u.email) {
      if (typed !== null) alert('Email did not match - deletion cancelled.');
      return;
    }
    try {
      await api.deleteAdminUser(u.id);
      fetchUsers();
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      alert(axiosError.response?.data?.detail || axiosError.response?.data?.error?.message || 'Failed');
    }
  };

  const createUser = async () => {
    try {
      await api.createAdminUser(createForm);
      setShowCreate(false);
      setCreateForm({ email: '', name: '', password: '', role: 'user' });
      setPage(1);
      fetchUsers();
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { error?: { message?: string }; detail?: string } };
      };
      setError(
        axiosError.response?.data?.error?.message ||
          axiosError.response?.data?.detail ||
          'Create failed'
      );
    }
  };

  const inputCls =
    'rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white';
  const labelCls = 'text-xs font-medium text-gray-500 dark:text-gray-400';

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          placeholder="Search email or name..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className={`${inputCls} w-64`}
        />
        <select value={roleFilter} onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }} className={inputCls}>
          <option value="">All roles</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
        </select>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className={inputCls}>
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <span className="text-sm text-gray-500 dark:text-gray-400">{total} user(s)</span>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="ml-auto rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          {showCreate ? 'Cancel' : '+ Add user'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/30 p-3 text-sm text-red-700 dark:text-red-300">
          {error}
          <button onClick={() => setError('')} className="ml-3 underline">dismiss</button>
        </div>
      )}

      {/* Create panel */}
      {showCreate && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5 space-y-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Create user</h3>
          <div className="flex flex-wrap gap-3">
            <input
              type="email" placeholder="Email *" value={createForm.email}
              onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
              className={`${inputCls} w-64`}
            />
            <input
              placeholder="Name" value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              className={`${inputCls} w-48`}
            />
            <input
              type="password" placeholder="Password (min 8) *" value={createForm.password}
              onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
              className={`${inputCls} w-56`}
            />
            <select
              value={createForm.role}
              onChange={(e) => setCreateForm({ ...createForm, role: e.target.value as 'admin' | 'user' })}
              className={inputCls}
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
            <button
              onClick={createUser}
              disabled={!createForm.email || createForm.password.length < 8}
              className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </div>
      )}

      {/* Users table */}
      {isLoading ? (
        <Skeleton rows={3} />
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead>
              <tr className="text-left text-xs uppercase text-gray-500 dark:text-gray-400">
                <th className="px-4 py-2.5">User</th>
                <th className="px-4 py-2.5">Role</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5">Plan</th>
                <th className="px-4 py-2.5">Billing</th>
                <th className="px-4 py-2.5">Usage (C/L/E)</th>
                <th className="px-4 py-2.5">Last login</th>
                <th className="px-4 py-2.5">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {users.map((u) => {
                const isSelf = me?.id === u.id;
                if (editingId === u.id && editForm) {
                  return (
                    <tr key={u.id} className="bg-indigo-50/50 dark:bg-indigo-900/10">
                      <td colSpan={8} className="px-4 py-4">
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                          <div>
                            <label className={labelCls}>Name</label>
                            <input
                              value={editForm.name}
                              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                              className={`${inputCls} mt-1 w-full`}
                            />
                          </div>
                          <div>
                            <label className={labelCls}>Role</label>
                            <select
                              value={editForm.role}
                              disabled={isSelf}
                              onChange={(e) =>
                                setEditForm({ ...editForm, role: e.target.value as 'admin' | 'user' })
                              }
                              className={`${inputCls} mt-1 w-full`}
                            >
                              <option value="user">User</option>
                              <option value="admin">Admin</option>
                            </select>
                          </div>
                          <div>
                            <label className={labelCls}>Plan</label>
                            <select
                              value={editForm.plan}
                              onChange={(e) => setEditForm({ ...editForm, plan: e.target.value })}
                              className={`${inputCls} mt-1 w-full`}
                            >
                              {PLANS.map((p) => <option key={p} value={p}>{p}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className={labelCls}>Billing status</label>
                            <select
                              value={editForm.billing_status}
                              onChange={(e) => setEditForm({ ...editForm, billing_status: e.target.value })}
                              className={`${inputCls} mt-1 w-full`}
                            >
                              {BILLING_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className={labelCls}>New password (leave blank to keep)</label>
                            <input
                              type="password" placeholder="min 8 chars" value={editForm.password}
                              onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                              className={`${inputCls} mt-1 w-full`}
                            />
                          </div>
                          <div className="flex items-end">
                            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                              <input
                                type="checkbox" checked={editForm.is_active} disabled={isSelf}
                                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                              />
                              Active
                            </label>
                          </div>
                          <div className="sm:col-span-2">
                            <label className={labelCls}>Billing notes</label>
                            <textarea
                              rows={2} value={editForm.billing_notes}
                              onChange={(e) => setEditForm({ ...editForm, billing_notes: e.target.value })}
                              className={`${inputCls} mt-1 w-full`}
                            />
                          </div>
                        </div>
                        <div className="mt-4 flex gap-2">
                          <button
                            onClick={() => saveEdit(u)}
                            className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => { setEditingId(null); setEditForm(null); }}
                            className="rounded-md border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-sm text-gray-600 dark:text-gray-300"
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                }
                return (
                  <tr key={u.id} className={!u.is_active ? 'opacity-60' : ''}>
                    <td className="px-4 py-2.5">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {u.email} {isSelf && <span className="text-xs text-gray-400">(you)</span>}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">{u.name || '-'}</div>
                    </td>
                    <td className="px-4 py-2.5"><StatusBadge status={u.role} /></td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={u.is_active ? 'active' : 'paused'} />
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300">{u.plan}</td>
                    <td className="px-4 py-2.5"><StatusBadge status={u.billing_status} /></td>
                    <td className="px-4 py-2.5 text-sm text-gray-500 dark:text-gray-400">
                      {u.campaigns_count} / {u.leads_count} / {u.emails_count}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500 dark:text-gray-400">
                      {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'never'}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex gap-2 text-sm">
                        <button
                          onClick={() => { setEditingId(u.id); setEditForm(toForm(u)); }}
                          className="text-indigo-600 dark:text-indigo-400 hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => toggleActive(u)}
                          disabled={isSelf}
                          className="text-amber-600 dark:text-amber-400 hover:underline disabled:opacity-40 disabled:no-underline"
                        >
                          {u.is_active ? 'Deactivate' : 'Reactivate'}
                        </button>
                        <button
                          onClick={() => deleteUser(u)}
                          disabled={isSelf}
                          className="text-red-600 dark:text-red-400 hover:underline disabled:opacity-40 disabled:no-underline"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {users.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                    No users match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-end gap-3 text-sm">
          <button
            onClick={() => setPage(page - 1)} disabled={page <= 1}
            className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1 disabled:opacity-40 text-gray-700 dark:text-gray-300"
          >
            Previous
          </button>
          <span className="text-gray-500 dark:text-gray-400">Page {page} of {pages}</span>
          <button
            onClick={() => setPage(page + 1)} disabled={page >= pages}
            className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1 disabled:opacity-40 text-gray-700 dark:text-gray-300"
          >
            Next
          </button>
        </div>
      )}

      <p className="text-xs text-gray-400 dark:text-gray-500">
        Usage columns: Campaigns / Leads / Emails sent. Deleting a user permanently removes
        all their data (cascade). Deactivating only blocks sign-in.
      </p>
    </div>
  );
}
