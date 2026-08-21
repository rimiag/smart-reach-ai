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
  created_at: string;
  last_login?: string;
}

export interface UserWithToken extends User {
  access_token: string;
  refresh_token: string;
  token_type: string;
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
