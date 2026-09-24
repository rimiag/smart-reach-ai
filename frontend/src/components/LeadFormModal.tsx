'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { Campaign, Lead } from '@/types';

interface LeadFormModalProps {
  mode: 'create' | 'edit';
  lead?: Lead;
  onClose: () => void;
  /** Receives the saved/created lead so callers can refresh or select it */
  onSaved: (lead: Lead) => void;
}

/**
 * Create a lead manually, or edit one (including re-assigning it to another
 * campaign). Manual leads get keyword "manual" and their website as source,
 * which satisfies the crawler-era required fields.
 */
export default function LeadFormModal({ mode, lead, onClose, onSaved }: LeadFormModalProps) {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(true);
  const [campaignId, setCampaignId] = useState<number>(lead?.campaign_id ?? 0);
  const [organizationName, setOrganizationName] = useState(lead?.organization_name ?? '');
  const [website, setWebsite] = useState(lead?.website ?? '');
  const [email, setEmail] = useState(lead?.email ?? '');
  const [phone, setPhone] = useState(lead?.phone ?? '');
  const [contactName, setContactName] = useState(lead?.contact_name ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .getCampaigns({ per_page: 100 })
      .then((res) => {
        const data = res.data as { items?: Campaign[] };
        setCampaigns(data.items || []);
      })
      .catch(() => setError('Failed to load campaigns'))
      .finally(() => setCampaignsLoading(false));
  }, []);

  const handleSave = async () => {
    if (!campaignId || !organizationName.trim() || !website.trim()) return;
    setSaving(true);
    setError('');
    try {
      if (mode === 'create') {
        const response = await api.createLead({
          campaign_id: campaignId,
          organization_name: organizationName.trim(),
          website: website.trim(),
          email: email.trim() || undefined,
          phone: phone.trim() || undefined,
          contact_name: contactName.trim() || undefined,
          keyword: 'manual',
          source_url: website.trim(),
        });
        onSaved(response.data as Lead);
      } else if (lead) {
        const response = await api.updateLead(lead.id, {
          campaign_id: campaignId,
          organization_name: organizationName.trim(),
          website: website.trim(),
          email: email.trim() || undefined,
          phone: phone.trim() || undefined,
          contact_name: contactName.trim() || undefined,
        });
        onSaved(response.data as Lead);
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to save lead');
    } finally {
      setSaving(false);
    }
  };

  const canSave = Boolean(campaignId) && organizationName.trim() !== '' && website.trim() !== '';

  const inputClass =
    'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500';

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
            {mode === 'create' ? '+ New lead' : 'Edit lead'}
          </h2>
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

          {campaignsLoading ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading campaigns...</p>
          ) : campaigns.length === 0 ? (
            <p className="text-sm text-gray-600 dark:text-gray-300">
              You need a campaign first -{' '}
              <Link href="/campaigns/new" className="text-blue-600 hover:text-blue-700 font-medium">
                create one
              </Link>{' '}
              and come back.
            </p>
          ) : (
            <>
              <div>
                <label htmlFor="lead-form-campaign" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Campaign *
                </label>
                <select
                  id="lead-form-campaign"
                  value={campaignId || ''}
                  onChange={(e) => setCampaignId(Number(e.target.value))}
                  className={inputClass}
                >
                  <option value="">Select a campaign</option>
                  {campaigns.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                {mode === 'edit' && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Pick a different campaign to move this lead to it.
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label htmlFor="lead-form-org" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Organization *
                  </label>
                  <input
                    id="lead-form-org"
                    type="text"
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    className={inputClass}
                    placeholder="Acme Corporation"
                  />
                </div>
                <div>
                  <label htmlFor="lead-form-website" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Website *
                  </label>
                  <input
                    id="lead-form-website"
                    type="text"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    className={inputClass}
                    placeholder="https://example.com"
                  />
                </div>
                <div>
                  <label htmlFor="lead-form-email" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Email
                  </label>
                  <input
                    id="lead-form-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className={inputClass}
                    placeholder="contact@example.com"
                  />
                </div>
                <div>
                  <label htmlFor="lead-form-phone" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Phone
                  </label>
                  <input
                    id="lead-form-phone"
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className={inputClass}
                    placeholder="+1-555-123-4567"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="lead-form-contact" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Contact name
                </label>
                <input
                  id="lead-form-contact"
                  type="text"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  className={inputClass}
                  placeholder="John Doe"
                />
              </div>
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
            onClick={handleSave}
            disabled={saving || !canSave || campaigns.length === 0}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            {saving ? 'Saving...' : mode === 'create' ? 'Create lead' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
