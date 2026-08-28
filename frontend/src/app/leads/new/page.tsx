'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { Campaign } from '@/types';

function NewLeadContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const campaignIdParam = searchParams.get('campaign_id');

  const [formData, setFormData] = useState({
    organization_name: '',
    website: '',
    email: '',
    phone: '',
    campaign_id: campaignIdParam ? Number(campaignIdParam) : 0,
    keyword: '',
    source_url: '',
    contact_page_url: '',
    contact_name: '',
    job_title: '',
    department: '',
    country: '',
    city: '',
    lead_score: 50,
    ai_reasoning: '',
  });

  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [campaignsLoading, setCampaignsLoading] = useState(true);

  useEffect(() => {
    const fetchCampaigns = async () => {
      try {
        setCampaignsLoading(true);
        const response = await api.getCampaigns();
        setCampaigns(response.data.items || []);
        if (!formData.campaign_id && response.data.items?.length > 0) {
          setFormData(prev => ({ ...prev, campaign_id: response.data.items[0].id }));
        }
      } catch {
        setError('Failed to load campaigns');
      } finally {
        setCampaignsLoading(false);
      }
    };
    fetchCampaigns();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? (value ? Number(value) : 0) : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await api.createLead({
        organization_name: formData.organization_name,
        website: formData.website,
        email: formData.email || undefined,
        phone: formData.phone || undefined,
        campaign_id: formData.campaign_id,
        keyword: formData.keyword,
        source_url: formData.source_url,
        contact_page_url: formData.contact_page_url || undefined,
        contact_name: formData.contact_name || undefined,
        job_title: formData.job_title || undefined,
        department: formData.department || undefined,
        country: formData.country || undefined,
        city: formData.city || undefined,
        lead_score: formData.lead_score,
        ai_reasoning: formData.ai_reasoning || undefined,
      });
      router.push(`/leads?campaign_id=${formData.campaign_id}`);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Failed to create lead');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl mx-auto">
          <div className="mb-8">
            <Link
              href={formData.campaign_id ? `/leads?campaign_id=${formData.campaign_id}` : '/campaigns'}
              className="text-blue-600 hover:text-blue-700 font-medium text-sm"
            >
              ← Back to Leads
            </Link>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
              Create New Lead
            </h1>

            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-md mb-6">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Required Fields */}
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white border-b pb-2">
                  Required Information
                </h2>

                <div>
                  <label htmlFor="campaign_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Campaign *
                  </label>
                  {campaignsLoading ? (
                    <select disabled className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700">
                      <option>Loading campaigns...</option>
                    </select>
                  ) : (
                    <select
                      id="campaign_id"
                      name="campaign_id"
                      value={formData.campaign_id}
                      onChange={handleChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">Select a campaign</option>
                      {campaigns.map(campaign => (
                        <option key={campaign.id} value={campaign.id}>
                          {campaign.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="organization_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Organization Name *
                    </label>
                    <input
                      type="text"
                      id="organization_name"
                      name="organization_name"
                      value={formData.organization_name}
                      onChange={handleChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Acme Corporation"
                    />
                  </div>

                  <div>
                    <label htmlFor="website" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Website *
                    </label>
                    <input
                      type="url"
                      id="website"
                      name="website"
                      value={formData.website}
                      onChange={handleChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="https://example.com"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="keyword" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Keyword *
                    </label>
                    <input
                      type="text"
                      id="keyword"
                      name="keyword"
                      value={formData.keyword}
                      onChange={handleChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="e.g., SaaS lead generation"
                    />
                  </div>

                  <div>
                    <label htmlFor="source_url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Source URL *
                    </label>
                    <input
                      type="url"
                      id="source_url"
                      name="source_url"
                      value={formData.source_url}
                      onChange={handleChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="https://example.com/page"
                    />
                  </div>
                </div>
              </div>

              {/* Contact Information */}
              <div className="space-y-4 pt-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white border-b pb-2">
                  Contact Information
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="contact_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Contact Name
                    </label>
                    <input
                      type="text"
                      id="contact_name"
                      name="contact_name"
                      value={formData.contact_name}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="John Doe"
                    />
                  </div>

                  <div>
                    <label htmlFor="job_title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Job Title
                    </label>
                    <input
                      type="text"
                      id="job_title"
                      name="job_title"
                      value={formData.job_title}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Marketing Manager"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="contact@example.com"
                    />
                  </div>

                  <div>
                    <label htmlFor="phone" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Phone
                    </label>
                    <input
                      type="tel"
                      id="phone"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="+1-555-123-4567"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label htmlFor="department" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Department
                    </label>
                    <input
                      type="text"
                      id="department"
                      name="department"
                      value={formData.department}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Marketing"
                    />
                  </div>

                  <div>
                    <label htmlFor="city" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      City
                    </label>
                    <input
                      type="text"
                      id="city"
                      name="city"
                      value={formData.city}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="San Francisco"
                    />
                  </div>

                  <div>
                    <label htmlFor="country" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Country
                    </label>
                    <input
                      type="text"
                      id="country"
                      name="country"
                      value={formData.country}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="United States"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="contact_page_url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Contact Page URL
                  </label>
                  <input
                    type="url"
                    id="contact_page_url"
                    name="contact_page_url"
                    value={formData.contact_page_url}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="https://example.com/contact"
                  />
                </div>
              </div>

              {/* AI Qualification */}
              <div className="space-y-4 pt-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white border-b pb-2">
                  AI Qualification
                </h2>

                <div>
                  <label htmlFor="lead_score" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Lead Score (0-100): {formData.lead_score}
                  </label>
                  <input
                    type="range"
                    id="lead_score"
                    name="lead_score"
                    min="0"
                    max="100"
                    value={formData.lead_score}
                    onChange={handleChange}
                    className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                    <span>Low Quality</span>
                    <span>High Quality</span>
                  </div>
                </div>

                <div>
                  <label htmlFor="ai_reasoning" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    AI Reasoning
                  </label>
                  <textarea
                    id="ai_reasoning"
                    name="ai_reasoning"
                    value={formData.ai_reasoning}
                    onChange={handleChange}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Explain why this lead is qualified..."
                  />
                </div>
              </div>

              {/* Submit */}
              <div className="flex justify-end gap-4 pt-6 border-t border-gray-200 dark:border-gray-700">
                <Link
                  href={formData.campaign_id ? `/leads?campaign_id=${formData.campaign_id}` : '/campaigns'}
                  className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-md transition-colors"
                >
                  Cancel
                </Link>
                <button
                  type="submit"
                  disabled={isLoading || !formData.campaign_id}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-md transition-colors"
                >
                  {isLoading ? 'Creating...' : 'Create Lead'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function NewLeadPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-gray-50 dark:bg-gray-900" />}>
      <NewLeadContent />
    </Suspense>
  );
}
