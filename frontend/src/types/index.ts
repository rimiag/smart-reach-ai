/**
 * Type definitions for the AI Lead Generation Platform
 */

// -----------------------------------------------------------------------------
// User Types
// -----------------------------------------------------------------------------
export interface User {
  id: number;
  email: string;
  name?: string;
  role: 'admin' | 'user';
  is_active: boolean;
  is_verified?: boolean;
  /** "hold" = new signup awaiting admin approval (read-only) */
  account_status?: 'hold' | 'active';
  created_at: string;
  last_login?: string;
  plan?: string;
  billing_status?: string;
}

export interface UserWithToken extends User {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// -----------------------------------------------------------------------------
// API Usage Types (admin)
// -----------------------------------------------------------------------------
export interface ApiUsageInfo {
  configured: boolean;
  used: number | null;
  limit: number | null;
  remaining: number | null;
  source: 'live' | 'counter';
  error: string | null;
}

export interface ApiUsage {
  serpapi: ApiUsageInfo;
  gemini: ApiUsageInfo;
  email: {
    configured: boolean;
    sent_this_month: number;
    failed_this_month: number;
  };
}

// -----------------------------------------------------------------------------
// Admin Types
// -----------------------------------------------------------------------------
export interface AdminUser {
  id: number;
  email: string;
  name?: string;
  role: 'admin' | 'user';
  is_active: boolean;
  created_at: string;
  last_login?: string;
  plan: string;
  billing_status: string;
  billing_notes?: string;
  account_status: 'hold' | 'active';
  campaigns_count: number;
  leads_count: number;
  emails_count: number;
}

export interface AdminUsersResponse {
  items: AdminUser[];
  total: number;
  page: number;
  per_page: number;
}

export interface DayCount {
  date: string;
  count: number;
}

export interface RecentSignup {
  id: number;
  email: string;
  name?: string;
  role: 'admin' | 'user';
  created_at: string;
}

export interface OverviewStats {
  users_total: number;
  users_active: number;
  users_admins: number;
  campaigns_total: number;
  leads_total: number;
  emails_total: number;
  replies_total: number;
  suppressions_total: number;
  emails_last_7_days: DayCount[];
  recent_signups: RecentSignup[];
}

export interface SystemStatus {
  database: boolean;
  redis: boolean;
  celery_online: boolean;
  celery_workers: string[];
  integrations: Record<string, boolean>;
}

// -----------------------------------------------------------------------------
// Campaign Types
// -----------------------------------------------------------------------------
export type CampaignStatus = 'draft' | 'researching' | 'ready' | 'active' | 'paused' | 'completed';

export interface Campaign {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  status: CampaignStatus;
  keywords: string[];
  settings?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CampaignCreate {
  name: string;
  description?: string;
  keywords: string[];
}

export interface CampaignStats {
  websites_found: number;
  websites_crawled: number;
  contacts_found: number;
  leads_created: number;
  leads_qualified: number;
  emails_sent: number;
  emails_delivered: number;
  emails_opened: number;
  replies_received: number;
  interested_leads: number;
  unsubscribes: number;
  bounces: number;
}

// -----------------------------------------------------------------------------
// Research Progress Types
// -----------------------------------------------------------------------------
export type ResearchStatus = CampaignStatus | 'failed';

export interface ResearchProgress {
  campaign_id: number;
  status: ResearchStatus;
  current_step: string;
  progress_percentage: number;
  websites_found: number;
  websites_crawled: number;
  contacts_found: number;
  leads_created: number;
  keywords_total: number;
  keywords_completed: number;
  started_at?: string;
  estimated_completion?: string;
  error?: string | null;
}

// -----------------------------------------------------------------------------
// Analytics Types
// -----------------------------------------------------------------------------
export interface DashboardStats {
  campaigns_total: number;
  campaigns_active: number;
  leads_total: number;
  leads_new: number;
  leads_approved: number;
  leads_rejected: number;
  websites_discovered: number;
  websites_crawled: number;
}

export interface ReplyItem {
  id: number;
  campaign_id: number;
  lead_id: number;
  from_email: string;
  from_name?: string;
  subject?: string;
  body: string;
  category: string;
  ai_summary?: string;
  status: 'unread' | 'read';
  received_at?: string;
  created_at?: string;
}

export interface ReplyAnalytics {
  total_replies: number;
  unread_replies: number;
  replies_last_7_days: number;
  by_category: Record<string, number>;
  reply_rate_percent: number;
  emails_sent: number;
  last_reply_at?: string | null;
}

export interface CampaignComparison {
  campaign_id: number;
  campaign_name: string;
  status: CampaignStatus;
  leads_total: number;
  leads_new: number;
  leads_approved: number;
  websites_discovered: number;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Lead Types
// -----------------------------------------------------------------------------
export type LeadStatus = 'new' | 'researching' | 'qualified' | 'review' | 'approved' | 'rejected' | 'scheduled' | 'sent' | 'replied' | 'interested' | 'not_interested' | 'unsubscribed' | 'bounced' | 'do_not_contact';

export interface Lead {
  id: number;
  campaign_id: number;
  user_id: number;
  keyword: string;
  source_url: string;
  contact_page_url?: string;
  organization_name: string;
  website: string;
  contact_name?: string;
  job_title?: string;
  department?: string;
  email?: string;
  phone?: string;
  country?: string;
  city?: string;
  lead_score: number;
  ai_reasoning?: string;
  ai_research_summary?: string;
  status: LeadStatus;
  generated_email?: string;
  email_template_id?: number;
  emails_sent: number;
  messages_sent: number;
  last_emailed_at?: string;
  last_contacted_at?: string;
  do_not_contact: boolean;
  unsubscribed_at?: string;
  created_at: string;
  updated_at: string;
  discovered_at: string;
  qualified_at?: string;
  approved_at?: string;
  notes?: string;
}

export interface LeadCreate {
  organization_name: string;
  website: string;
  email?: string;
  phone?: string;
  campaign_id: number;
  keyword: string;
  source_url: string;
  contact_page_url?: string;
  contact_name?: string;
  job_title?: string;
  department?: string;
  country?: string;
  city?: string;
  lead_score?: number;
  ai_reasoning?: string;
}

// -----------------------------------------------------------------------------
// Email Types
// -----------------------------------------------------------------------------
export type EmailStatus = 'draft' | 'approved' | 'scheduled' | 'sent' | 'failed' | 'bounced';
export type EmailTemplateType = 'professional' | 'problem_solution' | 'technical' | 'research_team' | 'consulting' | 'follow_up';

export interface EmailTemplate {
  id: number;
  campaign_id: number;
  name: string;
  type: EmailTemplateType;
  subject: string;
  body: string;
  variables?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface GeneratedEmail {
  id: number;
  campaign_id: number;
  lead_id: number;
  template_id?: number;
  subject: string;
  body: string;
  personalization_data?: Record<string, unknown>;
  status: EmailStatus;
  scheduled_at?: string;
  sent_at?: string;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Common Types
// -----------------------------------------------------------------------------
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ApiError {
  error: {
    code: number;
    message: string;
  };
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  app: string;
  environment: string;
  version: string;
}
