'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

const FORMATS = [
  { value: 'csv', label: 'CSV' },
  { value: 'excel', label: 'Excel' },
  { value: 'json', label: 'JSON' },
];

interface ExportButtonProps {
  campaignId: number;
}

export default function ExportButton({ campaignId }: ExportButtonProps) {
  const [format, setFormat] = useState('csv');
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState('');

  const handleExport = async () => {
    setIsExporting(true);
    setError('');
    try {
      const response = await api.exportLeads({ campaign_id: campaignId, format });

      // Prefer the server-provided filename, fall back to a local default.
      const disposition: string = response.headers['content-disposition'] || '';
      const match = /filename="([^"]+)"/.exec(disposition);
      const extension = format === 'excel' ? 'xlsx' : format;
      const filename = match ? match[1] : `leads_export.${extension}`;

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: { message?: string } } } };
      setError(axiosError.response?.data?.error?.message || 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <select
        value={format}
        onChange={(e) => setFormat(e.target.value)}
        disabled={isExporting}
        className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Export format"
      >
        {FORMATS.map((f) => (
          <option key={f.value} value={f.value}>
            {f.label}
          </option>
        ))}
      </select>
      <button
        onClick={handleExport}
        disabled={isExporting}
        className="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white px-4 py-2 rounded-md transition-colors flex items-center gap-2 text-sm"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        {isExporting ? 'Exporting...' : 'Export'}
      </button>
      {error && <span className="text-sm text-red-600 dark:text-red-400">{error}</span>}
    </div>
  );
}
