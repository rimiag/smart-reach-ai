/**
 * API Client Configuration
 *
 * Axios-based HTTP client with authentication and error handling.
 */
import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type { ApiError } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Create and configure axios instance
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  // Remove withCredentials to avoid CORS preflight issues
  // We'll use Authorization header instead
  withCredentials: false,
});

/**
 * Request interceptor to add auth token
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Only access localStorage in browser environment
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Response interceptor for error handling
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Handle 401 Unauthorized - try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;

        localStorage.setItem('access_token', access_token);
        if (newRefreshToken) {
          localStorage.setItem('refresh_token', newRefreshToken);
        }

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * API client methods
 */
export const api = {
  // Health check
  getHealth: () => apiClient.get('/../../health'),

  // Authentication
  register: (data: { email: string; password: string; name?: string }) =>
    apiClient.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    apiClient.post('/auth/login', data),
  logout: () => apiClient.post('/auth/logout'),
  getCurrentUser: () => apiClient.get('/auth/me'),

  // Campaigns
  getCampaigns: (params?: Record<string, unknown>) =>
    apiClient.get('/campaigns', { params }),
  createCampaign: (data: { name: string; description?: string; keywords: string[] }) =>
    apiClient.post('/campaigns', data),
  getCampaign: (id: number) => apiClient.get(`/campaigns/${id}`),
  updateCampaign: (id: number, data: Partial<{ name: string; description: string; keywords: string[] }>) =>
    apiClient.put(`/campaigns/${id}`, data),
  deleteCampaign: (id: number) => apiClient.delete(`/campaigns/${id}`),
  startResearch: (id: number) => apiClient.post(`/campaigns/${id}/start`),
  getResearchProgress: (id: number) => apiClient.get(`/campaigns/${id}/progress`),
  getCampaignStats: (id: number) => apiClient.get(`/campaigns/${id}/stats`),

  // Leads
  getLeads: (params?: Record<string, unknown>) =>
    apiClient.get('/leads', { params }),
  getLead: (id: number) => apiClient.get(`/leads/${id}`),
  updateLead: (id: number, data: Record<string, unknown>) =>
    apiClient.put(`/leads/${id}`, data),
  deleteLead: (id: number) => apiClient.delete(`/leads/${id}`),
  approveLead: (id: number) => apiClient.post(`/leads/${id}/approve`),
  rejectLead: (id: number) => apiClient.post(`/leads/${id}/reject`),
  bulkApprove: (data: { ids: number[] }) => apiClient.post('/leads/bulk-approve', data),
  bulkReject: (data: { ids: number[] }) => apiClient.post('/leads/bulk-reject', data),
  exportLeads: (params: Record<string, unknown>) =>
    apiClient.get('/leads/export', { params, responseType: 'blob' }),

  // Emails
  getEmails: (params?: Record<string, unknown>) =>
    apiClient.get('/emails', { params }),
  getEmail: (id: number) => apiClient.get(`/emails/${id}`),
  sendTestEmail: (data: { to: string }) => apiClient.post('/emails/send-test', data),

  // Suppression
  getSuppressionList: (params?: Record<string, unknown>) =>
    apiClient.get('/suppression', { params }),
  addToSuppression: (data: { email?: string; domain?: string; reason: string }) =>
    apiClient.post('/suppression', data),
  removeFromSuppression: (id: number) => apiClient.delete(`/suppression/${id}`),

  // Analytics
  getDashboardStats: () => apiClient.get('/analytics/dashboard'),
  getCampaignAnalytics: () => apiClient.get('/analytics/campaigns'),
  getReplyAnalytics: () => apiClient.get('/analytics/replies'),
};

export default apiClient;
