# SmartReach AI - Complete Development Plan

**Project:** AI-Powered B2B Lead Generation & Outreach Platform
**Version:** 0.1.0
**Last Updated:** 2026-08-31
**Status:** PHASE 5 COMPLETE (3 of 11 enhancements) - Follow-ups, AI Sales Assistant, Intent Detection

---

## 📊 Executive Summary

SmartReach AI is an intelligent B2B lead generation platform that discovers potential clients through web search, qualifies leads using AI, and manages personalized outreach campaigns.

**Current Progress:**
- ✅ Foundation (Authentication, Campaign CRUD, Frontend)
- ✅ Phase 1 Core (100% complete)
- ⏳ Phase 5 (3 of 11 enhancements delivered: follow-up sequences, AI sales assistant, intent detection)
- ✅ Phase 4 (Reply Detection & Analytics) - Complete
- ✅ Phase 2 (AI Qualification & Email Generation) - Complete
- ✅ Phase 3 (Email Sending & Human Approval) - Complete

**Architecture:**
```
Frontend (Next.js) → FastAPI Backend → MySQL Database
                              ↓
                         Celery Workers
                              ↓
                    AI Agents (Search, Crawl, Qualify, Outreach)
```

---

## 🎯 Development Phases Overview

| Phase | Focus | Status | Priority |
|-------|-------|--------|----------|
| **Foundation** | Auth, Campaigns | ✅ Complete | - |
| **Iteration 1.3** | Lead System | ✅ Complete | 🔥 High |
| **Iteration 1.4** | Search & Discovery | ✅ Complete | 🔥 High |
| **Iteration 1.5** | Crawling & Extraction | ✅ Complete | 🔥 High |
| **Iteration 1.6** | Export & Phase 1 Complete | ✅ Complete | 🔥 High |
| **Phase 2** | AI Qualification & Emails | ✅ Complete | Medium |
| **Phase 3** | Email Sending & Approval | ✅ Complete | Medium |
| **Phase 4** | Reply Detection & Analytics | ✅ Complete | Low |
| **Phase 5** | Future Enhancements | ✅ 3 Delivered | Low |

---

## ✅ COMPLETED - Foundation (Iteration 1.0 - 1.2)

### Iteration 1.0 - Project Foundation
| Task | File | Status |
|------|------|--------|
| Docker Compose setup | `docker-compose.yml` | ✅ |
| FastAPI application structure | `backend/app/main.py` | ✅ |
| Database base configuration | `backend/app/db/base.py` | ✅ |
| Configuration management | `backend/app/core/config.py` | ✅ |
| Security utilities | `backend/app/core/security.py` | ✅ |
| Next.js frontend setup | `frontend/` | ✅ |
| Tailwind CSS + shadcn/ui | `frontend/tailwind.config.ts` | ✅ |

### Iteration 1.1 - Authentication System
| Task | Backend | Frontend | Status |
|------|---------|----------|--------|
| User model | `models/user.py` | - | ✅ |
| User schema | `schemas/user.py` | `types/index.ts` | ✅ |
| Auth endpoints | `api/v1/auth.py` | - | ✅ |
| JWT middleware | `dependencies.py` | `lib/auth.ts` | ✅ |
| Login page | - | `app/login/page.tsx` | ✅ |
| Register page | - | `app/register/page.tsx` | ✅ |
| Auth hook | - | `hooks/useAuth.ts` | ✅ |

### Iteration 1.2 - Campaign System
| Task | Backend | Frontend | Status |
|------|---------|----------|--------|
| Campaign model | `models/campaign.py` | - | ✅ |
| Campaign schema | `schemas/campaign.py` | `types/index.ts` | ✅ |
| Campaign service | `services/campaign_service.py` | - | ✅ |
| Campaign API | `api/v1/campaigns.py` | - | ✅ |
| Campaign list | - | `app/campaigns/page.tsx` | ✅ |
| Create campaign | - | `app/campaigns/new/page.tsx` | ✅ |
| Campaign detail | - | `app/campaigns/[id]/page.tsx` | ✅ |

---

## ✅ COMPLETED - Iteration 1.3: Lead System

**Objective:** Create the lead database model and API for managing discovered leads.
**Completed:** 2026-08-20
**Status:** ✅ Full verified implementation

### Implementation Summary

| Task | Backend | Frontend | Status |
|------|---------|----------|--------|
| Lead model | `models/lead.py` | - | ✅ Verified |
| Lead schema | `schemas/lead.py` | `types/index.ts` | ✅ Fixed mismatch |
| Lead service | `services/lead_service.py` | - | ✅ Complete |
| Leads API | `api/v1/leads.py` | - | ✅ All endpoints working |
| Auth hook | - | `hooks/useAuth.ts` | ✅ Fixed login/register |
| Leads list page | - | `app/leads/page.tsx` | ✅ Working |
| Lead detail page | - | `app/leads/[id]/page.tsx` | ✅ Working |
| Database migration | `alembic/versions/001_*.py` | - | ✅ Fixed for MariaDB 10.1 |

### API Endpoints Implemented

All lead management endpoints are working:
- `GET /api/v1/leads` - List leads (with filters, pagination)
- `POST /api/v1/leads` - Create lead (for crawler)
- `GET /api/v1/leads/{id}` - Get lead details
- `PUT /api/v1/leads/{id}` - Update lead
- `DELETE /api/v1/leads/{id}` - Delete lead
- `POST /api/v1/leads/{id}/approve` - Approve for outreach
- `POST /api/v1/leads/{id}/reject` - Reject lead
- `POST /api/v1/leads/bulk-approve` - Bulk approve
- `POST /api/v1/leads/bulk-reject` - Bulk reject

### Frontend Pages Working

- `/leads?campaign_id={id}` - Campaign leads list with filtering
- `/leads/{id}` - Lead detail with approve/reject actions
- Full CRUD operations working
- Campaign to Leads navigation working

---

## ✅ COMPLETED - Iteration 1.4: Search & Discovery

**Objective:** Implement web search integration to discover relevant websites based on keywords.
**Completed:** 2026-08-31
**Status:** ✅ Fully implemented and verified end-to-end

### Implementation Summary

| # | Task | File | Status |
|---|------|------|--------|
| 1.4.1 | Celery configuration | `backend/app/tasks/celery_app.py` | ✅ Verified task routing |
| 1.4.2 | Search Agent | `backend/app/agents/search_agent.py` | ✅ Validation + dedup |
| 1.4.3 | Bing Search API | `backend/app/integrations/bing_search.py` | ✅ + Google & SerpAPI providers |
| 1.4.4 | Search task | `backend/app/tasks/search_tasks.py` | ✅ Celery + in-process dev fallback |
| 1.4.5 | Campaign start endpoint | `backend/app/api/v1/campaigns.py` | ✅ Fail-fast when no provider |
| 1.4.6 | Progress tracking | `backend/app/tasks/progress_tracker.py` | ✅ Redis-backed, degrades gracefully |
| 1.4.7 | Research results model | `backend/app/models/research_result.py` | ✅ + migration `002_research_results.py` |
| 1.4.8 | Frontend progress component | `frontend/src/components/ResearchProgress.tsx` | ✅ Live polling UI |

### How It Works

1. `POST /api/v1/campaigns/{id}/start` sets the campaign to `researching` and
   dispatches the search task (Celery `search` queue in Docker; in-process
   asyncio fallback when no Redis broker is available - laptop development).
2. The SearchAgent runs one search-provider query per keyword, filters junk
   (social networks, search engines, non-HTML documents) and dedupes domains.
3. One `research_results` row is stored per unique domain per campaign;
   cross-keyword duplicates and re-runs are skipped (idempotent).
4. Live progress (current keyword, % complete, websites found) is written to
   Redis and exposed via `GET /api/v1/campaigns/{id}/progress`; the endpoint
   falls back to database-derived counts when Redis has no entry.
5. On success the campaign moves to `ready`; on failure it is reset to `draft`
   with the error surfaced in the UI so research can be retried.

### Search Providers

Hosted Bing Search v7 was retired by Microsoft in August 2025, so three
interchangeable providers are implemented (`SEARCH_PROVIDER=auto` picks the
first configured one, in this order):

| Provider | Env vars | Notes |
|----------|----------|-------|
| SerpAPI (recommended) | `SERPAPI_KEY` | Paid, reliable Google results |
| Google Custom Search | `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` | 100 free queries/day |
| Bing v7-compatible | `BING_SEARCH_API_KEY` (+ optional `BING_SEARCH_ENDPOINT`) | For compatible endpoints only |

### Verification Performed

- Search agent unit checks (validation, dedup, provider parsing) - passed
- Full orchestration E2E against local MariaDB with a mocked provider:
  keyword search → filter → dedup → persistence → status transitions →
  idempotent re-run → failure path reset to draft - all passed
- Frontend `next build` (includes tsc) - passed
- Celery task registration and API routes - verified

---

## Iteration 1.4: Search & Discovery - Technical Specification (Implemented)

**Objective:** Implement web search integration to discover relevant websites based on keywords.

### Architecture

```
Keyword Input → Search Agent → Search API → Results Queue → Crawler
```

### Implementation Checklist

| # | Task | File | Estimate |
|---|------|------|----------|
| 1.4.1 | Configure Celery with Redis | `backend/app/tasks/celery_app.py` | 30 min |
| 1.4.2 | Create Search Agent base | `backend/app/agents/search_agent.py` | 45 min |
| 1.4.3 | Implement Bing Search API | `backend/app/integrations/bing_search.py` | 60 min |
| 1.4.4 | Create search task | `backend/app/tasks/search_tasks.py` | 45 min |
| 1.4.5 | Update campaign start endpoint | `backend/app/api/v1/campaigns.py` | 30 min |
| 1.4.6 | Progress tracking system | `backend/app/tasks/progress_tracker.py` | 45 min |
| 1.4.7 | Research results model | `backend/app/models/research_result.py` | 30 min |
| 1.4.8 | Frontend progress component | `frontend/src/components/ResearchProgress.tsx` | 45 min |

### Search Agent Specification

```python
class SearchAgent:
    """Agent for discovering websites based on keywords."""
    
    async def search(self, keyword: str, limit: int = 100) -> List[SearchResult]:
        """
        Search for websites relevant to the keyword.
        
        Args:
            keyword: Search term
            limit: Maximum results per keyword
            
        Returns:
            List of search results with URL, title, snippet
        """
        
    async def validate_result(self, result: SearchResult) -> bool:
        """Filter out irrelevant/low-quality results."""
        
    async def deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate domains across keywords."""
```

### Environment Variables Required

```env
# Search Provider (at least one required)
BING_SEARCH_API_KEY=your_bing_key
GOOGLE_SEARCH_API_KEY=your_google_key
GOOGLE_SEARCH_ENGINE_ID=your_cse_id
SERPAPI_KEY=your_serpapi_key

# Redis for Celery
REDIS_URL=redis://redis:6379/0
```

---

## ✅ COMPLETED - Iteration 1.5: Crawling & Extraction

**Objective:** Implement the web crawler to extract public business contact information and create leads.
**Completed:** 2026-09-02
**Status:** ✅ Fully implemented and verified end-to-end

### Implementation Summary

| # | Task | File | Status |
|---|------|------|--------|
| 1.5.1 | Crawler Agent | `backend/app/agents/crawler_agent.py` | ✅ Robots + rate limits + contact-page pipeline |
| 1.5.2 | Robots.txt handler | `backend/app/crawlers/robots_txt.py` | ✅ RFC 9309-style, per-domain cache |
| 1.5.3 | Contact page finder | `backend/app/crawlers/page_finder.py` | ✅ Link scoring (contact/team/impressum) |
| 1.5.4 | Email extractor | `backend/app/crawlers/email_extractor.py` | ✅ mailto + text, junk filtering |
| 1.5.5 | Phone extractor | `backend/app/crawlers/phone_extractor.py` | ✅ tel: + patterns, placeholder rejection |
| 1.5.6 | Crawling task | `backend/app/tasks/crawl_tasks.py` | ✅ Chained after search + standalone task |
| 1.5.7 | Data normalization | `backend/app/services/data_normalizer.py` | ✅ |
| 1.5.8 | Duplicate detection | `backend/app/services/duplicate_detector.py` | ✅ Per-campaign domain/email index |
| 1.5.9 | Lead creation | `backend/app/services/lead_creator.py` | ✅ |

### How It Works

Research (`Start Research`) now runs both phases in one go:

1. **Search phase** (Iteration 1.4): one search-provider query per keyword; discovered
   websites stored as `research_results` (status `discovered`).
2. **Crawl phase** (Iteration 1.5): each discovered website is visited politely -
   robots.txt checked first (RFC 9309-style handling), a shared rate limiter keeps
   `crawler_request_delay` between all requests, up to 4 contact-page candidates are
   examined per site (`crawler_max_workers` crawl concurrently).
3. Emails (mailto first), phones (tel: first) and the organization name
   (og:site_name / title) are extracted, normalized and de-duplicated.
4. Duplicate check: a per-campaign index of existing lead domains/emails skips
   organizations that already have a lead; new organizations become **leads**
   (status `new`, first email/phone stored).
5. Per-site outcomes are recorded on the research result (`crawled`, `skipped`
   robots/duplicate, `failed` + reason); progress tracking reports the crawl
   (90-100% range); the campaign ends `ready`.
6. Long runs are protected: Celery task time limits raised to 2h for both phases.

### Verification Performed

- Unit checks: email/phone extraction, junk + placeholder filtering, contact-page
  scoring, normalization, duplicate detection - passed
- Full E2E against a local test web server + real MariaDB: robots-blocked site
  skipped, lead created with correct org/email/phone/contact URL, in-run and
  cross-run duplicates skipped, campaign finalized `ready`, cleanup verified - passed
- Celery registration (search + crawl tasks), API imports, `next build` - passed

---

## Iteration 1.5: Crawling & Extraction - Technical Specification (Implemented)

**Objective:** Implement web crawler to extract public business contact information.

### Implementation Checklist

| # | Task | File | Estimate |
|---|------|------|----------|
| 1.5.1 | Create Crawler Agent | `backend/app/agents/crawler_agent.py` | 60 min |
| 1.5.2 | Robots.txt handler | `backend/app/crawlers/robots_txt.py` | 45 min |
| 1.5.3 | Contact page finder | `backend/app/crawlers/page_finder.py` | 45 min |
| 1.5.4 | Email extractor | `backend/app/crawlers/email_extractor.py` | 45 min |
| 1.5.5 | Phone extractor | `backend/app/crawlers/phone_extractor.py` | 30 min |
| 1.5.6 | Create crawling task | `backend/app/tasks/crawl_tasks.py` | 60 min |
| 1.5.7 | Data normalization | `backend/app/services/data_normalizer.py` | 30 min |
| 1.5.8 | Duplicate detection | `backend/app/services/duplicate_detector.py` | 45 min |
| 1.5.9 | Lead creation from data | `backend/app/services/lead_creator.py` | 45 min |

### Crawler Agent Specification

```python
class CrawlerAgent:
    """Agent for extracting business contact information from websites."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_second=2)
        self.robots_handler = RobotsTxtHandler()
        
    async def can_crawl(self, domain: str) -> bool:
        """Check robots.txt before crawling."""
        
    async def find_contact_pages(self, base_url: str) -> List[str]:
        """
        Find relevant pages on the website.
        Target pages: contact, about, team, staff, services
        """
        
    async def extract_contact_info(self, url: str) -> ContactInfo:
        """
        Extract publicly available business contact information.
        Returns: organization name, emails, phones, names, etc.
        """
        
    async def process_website(self, search_result: SearchResult) -> Optional[LeadData]:
        """Complete pipeline: validate → find pages → extract → normalize."""
```

### Contact Info Schema

```python
class ContactInfo(BaseModel):
    organization_name: Optional[str]
    website: str
    contact_name: Optional[str]
    job_title: Optional[str]
    department: Optional[str]
    emails: List[str]
    phones: List[str]
    country: Optional[str]
    city: Optional[str]
    contact_page_url: Optional[str]
    source_urls: List[str]
```

---

## ✅ COMPLETED - Iteration 1.6: Export & Phase 1 Complete

**Objective:** Implement export functionality and complete the Phase 1 MVP.
**Completed:** 2026-09-03
**Status:** ✅ Fully implemented and verified end-to-end - **PHASE 1 COMPLETE**

### Implementation Summary

| # | Task | File | Status |
|---|------|------|--------|
| 1.6.1 | CSV export | `backend/app/services/export_service.py` | ✅ UTF-8 BOM, plan-spec columns |
| 1.6.2 | Excel export | `backend/app/services/export_service.py` | ✅ openpyxl xlsx |
| 1.6.3 | JSON export | `backend/app/services/export_service.py` | ✅ |
| 1.6.4 | Export API endpoint | `backend/app/api/v1/leads.py` | ✅ `GET /leads/export` w/ filters + ownership |
| 1.6.5 | Frontend export UI | `frontend/src/components/ExportButton.tsx` | ✅ Format picker + blob download |
| 1.6.6 | Campaign statistics | `backend/app/services/analytics_service.py` | ✅ Real DB aggregates |
| 1.6.7 | Stats API endpoints | `backend/app/api/v1/analytics.py` | ✅ dashboard + campaigns + campaign stats |
| 1.6.8 | Dashboard stats UI | `frontend/src/components/StatsCards.tsx` | ✅ Dashboard + campaign detail pages |
| 1.6.9 | End-to-end testing | throwaway E2E suite | ✅ All passed |
| 1.6.10 | Phase 1 documentation | `PHASE1_COMPLETE.md` | ✅ |

### How It Works

- **Export**: `GET /api/v1/leads/export?campaign_id=&format=csv|excel|json`
  (optional status/score filters) returns a file download. Ownership is verified;
  CSV uses UTF-8 with BOM (Excel-safe); rows capped by `max_export_size`.
  The leads page gained a format picker + download button.
- **Statistics**: `GET /api/v1/analytics/dashboard` aggregates a user's campaigns,
  leads and research totals; `GET /api/v1/analytics/campaigns` returns one summary
  row per campaign; `GET /api/v1/campaigns/{id}/stats` now returns real DB counts
  (websites found/crawled, contacts, leads, emails sent, replies, bounces).
  The campaigns page shows dashboard stat cards; the campaign detail page shows
  per-campaign stat cards.
- Open/click tracking counters stay zero until Phase 4 adds tracking.

### Verification Performed

- Export round-trips: CSV re-parsed (headers + rows), xlsx loaded via openpyxl,
  JSON re-parsed; unsupported format rejected
- Analytics counts verified against fixture data (campaign stats, dashboard
  aggregates, per-campaign comparison)
- Endpoint-level tests (TestClient + auth override): all 3 formats download with
  Content-Disposition, 400 on bad format, 404 on unknown campaign, analytics
  endpoints return correct aggregates
- Frontend `next build` passed; DB left clean (no test fixtures)

---

## Iteration 1.6: Export & Phase 1 Complete - Technical Specification (Implemented)

**Objective:** Implement export functionality and complete Phase 1 MVP.

### Implementation Checklist

| # | Task | File | Estimate |
|---|------|------|----------|
| 1.6.1 | CSV export service | `backend/app/services/export_service.py` | 45 min |
| 1.6.2 | Excel export support | `backend/app/services/export_service.py` | 30 min |
| 1.6.3 | JSON export support | `backend/app/services/export_service.py` | 15 min |
| 1.6.4 | Export API endpoint | `backend/app/api/v1/leads.py` | 30 min |
| 1.6.5 | Frontend export UI | `frontend/src/components/ExportButton.tsx` | 30 min |
| 1.6.6 | Campaign statistics | `backend/app/services/analytics_service.py` | 60 min |
| 1.6.7 | Stats API endpoint | `backend/app/api/v1/analytics.py` | 30 min |
| 1.6.8 | Dashboard stats UI | `frontend/src/components/StatsCards.tsx` | 45 min |
| 1.6.9 | End-to-end testing | `tests/` | 60 min |
| 1.6.10 | Phase 1 documentation | `docs/PHASE1_COMPLETE.md` | 30 min |

### Export Format Specification

**CSV Format:**
```csv
Organization,Website,Contact Name,Job Title,Department,Email,Phone,Country,Contact URL,Source URL,Lead Score,Reason,Date Found
ABC Research,https://abc.edu,Dr. Smith,Research Director,Research IT,john@abc.edu,+1-555-0100,USA,https://abc.edu/contact,https://abc.edu/research,87,University research dept with REDCap,2026-08-10
```

**Campaign Statistics Response:**
```json
{
  "campaign_id": 1,
  "keywords": 5,
  "websites_discovered": 428,
  "websites_analyzed": 173,
  "leads_found": 82,
  "qualified_leads": 61,
  "emails_ready": 61,
  "emails_sent": 0,
  "opened": 0,
  "replies": 0,
  "interested": 0,
  "unsubscribed": 0,
  "bounced": 0
}
```

---

## ✅ COMPLETED - Phase 2: AI Qualification & Email Generation

**Objective:** Add AI-powered lead scoring and personalized email generation.
**Completed:** 2026-09-08
**Status:** ✅ Fully implemented and verified - works with Anthropic or OpenAI

### Implementation Summary

| # | Task | File | Status |
|---|------|------|--------|
| 2.1 | AI provider selection | `backend/app/integrations/ai_base.py` + config | ✅ `ai_provider=auto` picks anthropic→openai |
| 2.2 | OpenAI client | `backend/app/integrations/openai_client.py` | ✅ chat completions |
| 2.3 | Anthropic client | `backend/app/integrations/anthropic_client.py` | ✅ messages API (SDK 1.x) |
| 2.4 | Qualification Agent | `backend/app/agents/qualification_agent.py` | ✅ 0-100 score + reasoning + category |
| 2.5 | Email Generation Agent | `backend/app/agents/email_agent.py` | ✅ subject + personalized body |
| 2.6 | Template system | `backend/app/services/template_service.py` | ✅ 3 style variants, round-robin |
| 2.7 | Personalization service | `backend/app/services/personalization_service.py` | ✅ verified-facts-only context |
| 2.8 | Qualification task | `backend/app/tasks/qualify_tasks.py` | ✅ chained + celery "ai" queue |
| 2.9 | Email generation task | `backend/app/tasks/email_tasks.py` | ✅ chained + celery task |
| 2.10 | Lead review UI | `frontend/src/app/leads/review/page.tsx` | ✅ score-sorted decision queue |

### How It Works

- **Provider abstraction**: `LLMClient` interface with Anthropic + OpenAI
  implementations; `ai_provider=auto` picks the first configured
  (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`). Defaults: `claude-haiku-4-5` for
  bulk qualification, `claude-sonnet-5` for email writing (configurable).
- **Research pipeline is now**: search → crawl → **AI qualification** → finalize.
  New leads are scored 0-100 with reasoning (`[category] reasoning` in
  `ai_reasoning`) and move to `review`. Without a provider key the pipeline
  skips qualification silently and leads stay `new`.
- **Email drafts**: `generated_email` holds "Subject: ... \n\n body" for leads in
  `review`/`approved`. Templates (professional/short_direct/value_first) rotate
  per lead as structure hints; `{{SENDER_NAME}}`/`{{SENDER_COMPANY}}` remain as
  placeholders for Phase 3. Nothing is ever sent automatically.
- **Endpoints**: `POST /campaigns/{id}/qualify` + `/generate-emails` (queued),
  `POST /leads/{id}/qualify` + `/regenerate` (synchronous, 502 on AI failure,
  400 when no provider). Celery task registration is now explicit in
  `celery_app.py` (fixes a latent worker registration gap).
- **Frontend**: Review Queue page (score-sorted, approve/reject with email
  preview), lead detail AI + draft cards with Qualify/Generate/Regenerate
  buttons, campaign page action buttons.

### Verification Performed

- Unit checks: qualification/email response parsing (valid, malformed, score
  clamping), template round-robin and `{{VAR|default}}` rendering - passed
- Service E2E against real MariaDB with a fake AI client: new→review status
  transitions with scores, idempotent re-runs, draft generation with
  skip-existing and regenerate modes, placeholders preserved - passed
- Endpoint tests (TestClient + auth override): 400 fail-fast without provider,
  per-lead qualify and regenerate with fake provider - passed
- Frontend `next build`; celery registration (5 app tasks) - passed

---

## Phase 2: AI Qualification & Email Generation - Technical Specification (Implemented)

**Objective:** Add AI-powered lead scoring and personalized email generation.

### Implementation Checklist

| # | Task | File | Estimate |
|---|------|------|----------|
| 2.1 | Create AI provider config | `backend/app/core/ai_config.py` | 30 min |
| 2.2 | Implement OpenAI client | `backend/app/integrations/openai_client.py` | 45 min |
| 2.3 | Implement Anthropic client | `backend/app/integrations/anthropic_client.py` | 45 min |
| 2.4 | Create Qualification Agent | `backend/app/agents/qualification_agent.py` | 90 min |
| 2.5 | Create Email Generation Agent | `backend/app/agents/email_agent.py` | 90 min |
| 2.6 | Template system | `backend/app/services/template_service.py` | 60 min |
| 2.7 | Personalization service | `backend/app/services/personalization_service.py` | 45 min |
| 2.8 | Qualification task | `backend/app/tasks/qualification_tasks.py` | 45 min |
| 2.9 | Email generation task | `backend/app/tasks/email_tasks.py` | 45 min |
| 2.10 | Lead review UI | `frontend/src/app/leads/review/page.tsx` | 60 min |

### AI Qualification Prompt Template

```
You are a B2B lead qualification specialist. Analyze this organization and score it 0-100.

Organization: {organization_name}
Website: {website}
Keywords: {keywords}
Description: {website_description}
Contact: {contact_name} ({job_title})
Department: {department}

Consider:
- Relevance to the keywords
- Organization type (university, company, nonprofit)
- Likelihood of needing services related to keywords
- Quality of contact information
- Organization size indicators

Provide:
1. Score (0-100)
2. Reasoning (2-3 sentences)
3. Recommended service category

Response format:
SCORE: 87
REASONING: University research department with multiple clinical research programs and publicly listed REDCap-related activities.
CATEGORY: Educational/Research
```

### Email Templates

Generate 5-10 template variations:
1. Professional Introduction
2. Problem/Solution
3. Technical/IT focused
4. Research Team focused
5. Consulting focused
6. Short/Direct
7. Value-first
8. Case study
9. Question-based
10. Partnership opportunity

---

## ✅ COMPLETED - Phase 3: Email Sending & Human Approval

**Objective:** Integrate email providers and implement controlled sending with an approval workflow.
**Completed:** 2026-09-09
**Status:** ✅ Fully implemented and verified (SMTP provider; SES/Gmail/Graph deferred)

### Implementation Summary

| # | Task | File | Status |
|---|------|------|--------|
| 3.1 | Email provider config | `backend/app/core/config.py` (SMTP_* settings) | ✅ |
| 3.2 | SMTP integration | `backend/app/integrations/smtp_client.py` | ✅ aiosmtplib + STARTTLS |
| 3.3-3.5 | SES / Gmail API / Graph | deferred | ⏳ SMTP covers all providers via app passwords |
| 3.6 | Email service | `backend/app/services/email_service.py` | ✅ Rendering, suppression, limits, audit log |
| 3.7 | Sending limits | `backend/app/core/rate_limits.py` | ✅ Daily 50 / hourly 10 / cooldown 7d / pacing |
| 3.8 | Send task | `backend/app/tasks/send_tasks.py` | ✅ Celery + in-process fallback |
| 3.9 | Suppression model | `backend/app/models/suppression.py` | ✅ + `models/email_log.py` (send audit) |
| 3.10 | Suppression service | in `email_service` + `/api/v1/suppression` CRUD | ✅ |
| 3.11 | Approval + send API | `backend/app/api/v1/campaigns.py` | ✅ approve-all + send |
| 3.12 | Approval UI | `frontend/src/app/campaigns/[id]/approve/page.tsx` | ✅ Review & Send page |

### How It Works

1. **Approve**: `POST /campaigns/{id}/approve-all` moves every reviewed lead with an
   email draft to `approved`. Individual approvals also work per lead.
2. **Review & Send** (`/campaigns/{id}/approve`): sender identity form (name,
   company, from, reply-to - persisted in campaign settings), the send queue
   sorted by lead score, an explicit confirmation checkbox, and live progress.
3. **Send**: `POST /campaigns/{id}/send` validates SMTP config and the queue,
   then dispatches the send task. Per lead: suppression check → per-lead
   cooldown (7 days) → volume limits (50/day, 10/hour) → render final email
   (sender placeholders filled, unsubscribe footer appended) → SMTP send →
   `emails` audit row + lead status `sent`, `emails_sent++`.
4. **Compliance**: every email carries a working one-click unsubscribe link
   (`GET /api/v1/unsubscribe/{lead_id}/{token}` - no auth, token verified);
   unsubscribes land in the suppression list and the lead is marked
   `do_not_contact` + `unsubscribed`.
5. **Polite stopping**: a run that hits a limit stops and can be resumed later
   by clicking send again (sent leads are never re-sent).

### Verification Performed

- Unit: unsubscribe token determinism, final rendering (placeholder fill +
  footer), limits wiring - passed
- Service E2E with a fake SMTP transport against real MariaDB: sends with
  substitution, suppression skip, cooldown skip, audit rows, lead status
  transitions, non-approved leads untouched - passed
- Endpoint tests (TestClient + auth override): 400 SMTP-unconfigured,
  approve-all, send dispatch, send-log endpoint, unsubscribe valid/invalid
  token - passed
- Frontend `next build` + tsc - passed

---

## Phase 3: Email Sending & Human Approval - Technical Specification (Implemented)

**Objective:** Integrate email providers and implement controlled sending with approval workflow.

### Implementation Checklist

| # | Task | File | Estimate |
|---|------|------|----------|
| 3.1 | Email provider config | `backend/app/core/email_config.py` | 30 min |
| 3.2 | SMTP integration | `backend/app/integrations/smtp_client.py` | 45 min |
| 3.3 | Amazon SES integration | `backend/app/integrations/ses_client.py` | 60 min |
| 3.4 | Gmail API integration | `backend/app/integrations/gmail_client.py` | 90 min |
| 3.5 | Microsoft Graph integration | `backend/app/integrations/microsoft_client.py` | 90 min |
| 3.6 | Email service | `backend/app/services/email_service.py` | 60 min |
| 3.7 | Sending limits config | `backend/app/core/rate_limits.py` | 30 min |
| 3.8 | Campaign scheduler | `backend/app/tasks/campaign_scheduler.py` | 60 min |
| 3.9 | Suppression list model | `backend/app/models/suppression.py` | 30 min |
| 3.10 | Suppression service | `backend/app/services/suppression_service.py` | 45 min |
| 3.11 | Approval workflow API | `backend/app/api/v1/campaigns.py` | 45 min |
| 3.12 | Approval UI | `frontend/src/app/campaigns/[id]/approve/page.tsx` | 60 min |

### Email Sending Flow

```
User selects leads
      ↓
User reviews/edits emails
      ↓
User approves campaign
      ↓
Emails scheduled (respecting limits)
      ↓
Queue processes emails
      ↓
Check suppression list
      ↓
Send via provider
      ↓
Track delivery/bounce
      ↓
Update lead status
```

### Sending Limits Configuration

```python
DEFAULT_DAILY_LIMIT = 50
DEFAULT_PER_HOUR_LIMIT = 10
DEFAULT_MIN_DELAY_SECONDS = 60
DEFAULT_MAX_DELAY_SECONDS = 300

class SendingLimits:
    daily_limit: int = DEFAULT_DAILY_LIMIT
    per_hour_limit: int = DEFAULT_PER_HOUR_LIMIT
    min_delay: int = DEFAULT_MIN_DELAY_SECONDS
    max_delay: int = DEFAULT_MAX_DELAY_SECONDS
```

---

## ✅ COMPLETED - Phase 4: Reply Detection & Analytics

**Objective:** Monitor email replies and classify responses with AI; add analytics.
**Completed:** 2026-09-10
**Status:** ✅ Fully implemented and verified

### Implementation Summary

| # | Task | File | Status |
|---|------|------|--------|
| 4.1 | Webhook handler | `backend/app/api/v1/webhooks.py` | ✅ `POST /webhooks/reply` (+ optional secret) |
| 4.2 | Reply model | `backend/app/models/reply.py` | ✅ + migration `004_replies.py` |
| 4.3 | Reply monitoring service | `backend/app/services/reply_monitor.py` + `integrations/imap_client.py` | ✅ IMAP poll, thread/sender matching |
| 4.4 | Reply classification agent | `backend/app/agents/reply_agent.py` | ✅ 9 categories + keyword fallback |
| 4.5 | Analytics service | `backend/app/services/analytics_service.py` | ✅ + reply metrics |
| 4.6 | Analytics API | `backend/app/api/v1/analytics.py` | ✅ `/analytics/replies` implemented |
| 4.7 | Analytics UI | `frontend/src/app/analytics/page.tsx` | ✅ Metrics, comparison table, category bars |
| 4.8 | Reply inbox UI | `frontend/src/app/replies/page.tsx` | ✅ Category filters, mark read, manual check |

### How It Works

1. **Detection**: replies are matched to outreach in two ways - In-Reply-To /
   References Message-ID against the `emails` send log (precise), falling back to
   sender-address matching (most recent lead wins). Duplicates are suppressed via
   a unique thread reference.
2. **Classification**: the reply agent classifies into 9 categories (interested,
   not_interested, need_more_info, request_meeting, pricing_request,
   out_of_office, unsubscribe, wrong_contact, other) with a one-line summary.
   Keyword heuristics take over automatically when the AI provider is down.
3. **Lead impact**: interested/meeting/pricing/info → `interested`;
   not_interested → `not_interested`; unsubscribe → suppression list +
   `do_not_contact` + `unsubscribed`; others → `replied`.
4. **Polling**: Celery beat checks the mailbox every 15 minutes
   (`reply_check_enabled`, `reply_check_interval_minutes`); manual trigger via
   the Replies page ("Check mailbox now") or `GET /replies/check`.
5. **Analytics**: `/analytics` page shows reply metrics (total, unread, last 7
   days, reply rate) and a per-campaign comparison table; the site header now
   links Campaigns / Replies / Analytics.

### Verification Performed

- Unit: classification parsing (valid/invalid category), keyword fallback
  heuristics - passed
- Service E2E with fake AI + real MariaDB: thread match, sender match,
  duplicate skip, unknown-sender skip, lead status updates, unsubscribe ->
  suppression - passed
- Endpoint tests: replies list, check (IMAP-unconfigured skip), analytics
  payload, webhook ingest - passed
- Frontend tsc + `next build` - passed

---

## Phase 4: Reply Detection & Analytics - Technical Specification (Implemented)

**Objective:** Monitor email replies and classify responses with AI.

### Implementation Checklist

| # | Task | File | Estimate |
|---|------|------|----------|
| 4.1 | Email webhook handler | `backend/app/api/v1/webhooks.py` | 45 min |
| 4.2 | Reply model | `backend/app/models/reply.py` | 30 min |
| 4.3 | Reply monitoring service | `backend/app/services/reply_monitor.py` | 60 min |
| 4.4 | Reply classification agent | `backend/app/agents/reply_agent.py` | 60 min |
| 4.5 | Analytics dashboard data | `backend/app/services/analytics_service.py` | 60 min |
| 4.6 | Analytics API | `backend/app/api/v1/analytics.py` | 45 min |
| 4.7 | Frontend analytics | `frontend/src/app/analytics/page.tsx` | 90 min |
| 4.8 | Reply inbox UI | `frontend/src/app/replies/page.tsx` | 60 min |

### Reply Classification Categories

```python
REPLY_CATEGORIES = ENUM(
    'interested',           # Wants to learn more
    'not_interested',      # Not interested
    'need_more_info',      # Needs information
    'request_meeting',     # Wants to meet
    'pricing_request',     # Asking about pricing
    'out_of_office',       # Auto-reply OOO
    'unsubscribe',         # Wants to unsubscribe
    'wrong_contact',       # Wrong person
    'other',               # Other
    name='reply_category'
)
```

### Analytics Metrics

- Campaign performance
- Lead conversion rates
- Email open rates
- Response rates
- Qualified lead percentage
- Geography breakdown
- Time-based trends

---

## ✅ COMPLETED - Phase 5: Future Enhancements (3 Delivered)

**Objective:** Selected high-value enhancements from the Phase 5 menu.
**Completed:** 2026-09-10
**Status:** ✅ Follow-up sequences, AI sales assistant, lead intent detection

### 1. Follow-up Sequences (High priority)

- New: `follow_up_count` on leads (migration `005_follow_up_count.py`).
- **Eligibility**: status `sent`, last email older than `follow_up_after_days`
  (4), fewer than `follow_up_max_count` (2) follow-ups already drafted.
- AI drafts a short, polite follow-up (dedicated prompt, never repeats the
  first email) into `generated_email`, increments `follow_up_count`, and
  returns the lead to `review` for human approval - sending stays manual.
- Runs daily via Celery beat (`followup-sweep-daily`), on demand via
  `POST /campaigns/{id}/generate-followups`, or in-process locally.
- Config: `follow_up_enabled`, `follow_up_after_days`, `follow_up_max_count`.

### 2. AI Sales Assistant

- `POST /api/v1/assistant/ask` + `/assistant` chat page.
- Grounded strictly in the user's own data (volume metrics, campaigns, top
  leads by score, recent replies); refuses to invent numbers.

### 3. Lead Intent Detection

- `backend/app/services/intent_service.py`: fetches the lead's homepage
  during qualification and extracts buying signals (hiring, demo/trial CTAs,
  growth/funding, active buying language, campaign-keyword mentions).
- Signals sharpen the qualification prompt and appear in the lead's
  `ai_reasoning` ("| Signals: ..."). Gated by `intent_detection_enabled`
  (default on); fetch failures never break scoring.

### Other Phase 5 items (not built - need external accounts/credentials)

LinkedIn research, CRM sync (HubSpot/Salesforce), WhatsApp/SMS outreach,
Google Sheets sync, meeting scheduling, change/competitor monitoring.

### Verification Performed

- Follow-up sweep E2E with fake AI + real MariaDB: eligibility (recently
  emailed and maxed-out leads excluded), draft -> review with counter
  increment, idempotent re-sweeps - passed
- Intent signal extraction on canned page text; signals included in
  qualification prompts - passed
- Assistant endpoint (fake AI) returns grounded answers; 400 without provider
  - passed
- Frontend tsc + `next build` - passed

---

## Phase 5: Future Enhancements - Roadmap (3 of 11 Delivered)

**Objective:** Architecture supports future expansion.

### Planned Features

| Feature | Description | Priority |
|---------|-------------|----------|
| LinkedIn integration | Professional network research | Medium |
| CRM integration | HubSpot, Salesforce sync | High |
| WhatsApp Business | Alternative outreach channel | Medium |
| SMS outreach | Text message campaigns | Low |
| Google Sheets sync | Export to sheets | Medium |
| Follow-up sequences | Automated drip campaigns | High |
| Meeting scheduling | Calendly-like integration | Medium |
| Lead intent detection | Advanced intent analysis | Medium |
| Change monitoring | Website change alerts | Low |
| Competitor monitoring | Track competitor activity | Low |
| AI sales assistant | Chatbot for leads | Medium |

### Architecture Considerations

1. **Modular Agents** - Easy to add new AI agents
2. **Plugin System** - Email providers, search sources
3. **API Versioning** - `/api/v1/`, `/api/v2/`
4. **Webhooks** - External integrations
5. **Event Bus** - Async communication between services

---

## 🔐 Security & Compliance Checklist

### Required Security Features

| Feature | Status | Implementation |
|---------|--------|----------------|
| Authentication | ✅ | JWT with bcrypt |
| Rate limiting | ❌ | Add slowapi |
| CSRF protection | ❌ | Add middleware |
| Input validation | ⏳ | Partial (Pydantic) |
| SQL injection protection | ✅ | SQLAlchemy ORM |
| XSS protection | ✅ | Next.js automatic |
| CORS configuration | ✅ | Configured |
| Secrets encryption | ❌ | Need implementation |
| Audit logging | ❌ | Need implementation |
| API key rotation | ❌ | Need implementation |

### Compliance Requirements

- **CAN-SPAM**: Unsubscribe, physical address, opt-out
- **GDPR**: Data export, deletion, consent
- **robots.txt**: Respect crawler rules
- **Rate limits**: Respect website limits
- **Data retention**: Configurable cleanup

---

## 📁 Project Structure (Complete)

```
smart-reach-ai/
├── backend/
│   ├── app/
│   │   ├── agents/              # AI Agents
│   │   │   ├── search_agent.py ✅
│   │   │   ├── crawler_agent.py ✅
│   │   │   ├── qualification_agent.py
│   │   │   ├── email_agent.py
│   │   │   └── reply_agent.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py ✅
│   │   │       ├── campaigns.py ✅
│   │   │       ├── leads.py ✅
│   │   │       ├── emails.py ⏳
│   │   │       ├── suppression.py ⏳
│   │   │       ├── analytics.py ✅
│   │   │       ├── admin.py ✅
│   │   │       └── webhooks.py ⏳
│   │   ├── core/
│   │   │   ├── config.py ✅
│   │   │   ├── security.py ✅
│   │   │   ├── ai_config.py ⏳
│   │   │   └── rate_limits.py ⏳
│   │   ├── crawlers/            # Web Crawlers
│   │   │   ├── robots_txt.py ✅
│   │   │   ├── page_finder.py ✅
│   │   │   ├── email_extractor.py ✅
│   │   │   └── phone_extractor.py ⏳
│   │   ├── db/
│   │   │   ├── base.py ✅
│   │   │   └── migrations/ ⏳
│   │   ├── integrations/       # External Services
│   │   │   ├── openai_client.py ⏳
│   │   │   ├── anthropic_client.py ⏳
│   │   │   ├── bing_search.py ✅
│   │   │   ├── smtp_client.py ⏳
│   │   │   ├── ses_client.py ⏳
│   │   │   ├── gmail_client.py ⏳
│   │   │   └── microsoft_client.py ⏳
│   │   ├── models/
│   │   │   ├── user.py ✅
│   │   │   ├── campaign.py ✅
│   │   │   ├── lead.py ✅
│   │   │   ├── research_result.py ✅
│   │   │   ├── suppression.py ⏳
│   │   │   └── reply.py ⏳
│   │   ├── schemas/
│   │   │   ├── user.py ✅
│   │   │   ├── campaign.py ✅
│   │   │   ├── lead.py ✅
│   │   │   └── email.py ⏳
│   │   ├── services/
│   │   │   ├── campaign_service.py ✅
│   │   │   ├── lead_service.py ✅
│   │   │   ├── lead_creator.py ✅
│   │   │   ├── data_normalizer.py ✅
│   │   │   ├── duplicate_detector.py ✅
│   │   │   ├── email_service.py ⏳
│   │   │   ├── export_service.py ✅
│   │   │   ├── suppression_service.py ⏳
│   │   │   ├── personalization_service.py ⏳
│   │   │   ├── template_service.py ⏳
│   │   │   ├── data_normalizer.py ✅
│   │   │   └── duplicate_detector.py ⏳
│   │   ├── tasks/
│   │   │   ├── celery_app.py ⏳
│   │   │   ├── search_tasks.py ✅
│   │   │   ├── crawl_tasks.py ✅
│   │   │   ├── qualification_tasks.py ⏳
│   │   │   ├── email_tasks.py ⏳
│   │   │   └── campaign_scheduler.py ⏳
│   │   ├── dependencies.py ✅
│   │   └── main.py ✅
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt ✅
│   ├── Dockerfile ✅
│   └── pyproject.toml ✅
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx ✅
│   │   │   ├── page.tsx ✅
│   │   │   ├── login/ ✅
│   │   │   ├── register/ ✅
│   │   │   ├── campaigns/ ✅
│   │   │   ├── leads/ ✅
│   │   │   ├── analytics/ ⏳
│   │   │   └── replies/ ⏳
│   │   ├── components/          # Reusable components
│   │   │   ├── ui/ ✅ (shadcn)
│   │   │   ├── CampaignCard.tsx ⏳
│   │   │   ├── LeadCard.tsx ⏳
│   │   │   ├── ResearchProgress.tsx ✅
│   │   │   ├── ExportButton.tsx ✅
│   │   │   └── StatsCards.tsx ⏳
│   │   ├── hooks/
│   │   │   └── useAuth.ts ✅
│   │   ├── lib/
│   │   │   ├── api.ts ✅
│   │   │   └── auth.ts ✅
│   │   └── types/
│   │       └── index.ts ✅
│   ├── package.json ✅
│   ├── Dockerfile ✅
│   └── next.config.js ✅
├── docker-compose.yml ✅
├── .env.example ✅
├── README.md ✅
└── DEVELOPMENT_PLAN.md ✅ (this file)

✅ = Completed | ⏳ = In Progress/Not Started | ❌ = Missing
```

---

## 🚦 Next Steps

### Immediate (This Week)
1. ✅ Create detailed development plan (YOU ARE HERE)
2. ✅ Iteration 1.3: Lead System implementation
3. ✅ Iteration 1.4: Search & Discovery
4. ✅ Iteration 1.5: Crawling & Extraction
5. ✅ Iteration 1.6: Export & Phase 1 Complete

**Phase 1 MVP complete.** Core roadmap complete. Optional next steps: remaining Phase 5 enhancements, production deployment (OpenTofu plan), MariaDB upgrade.
5. ⏳ Iteration 1.6: Export & Phase 1 Complete

### Short-term (Next 2-4 Weeks)
- ✅ Phase 2: AI Qualification & Email Generation
- ✅ Phase 3: Email Sending & Human Approval
- ✅ Phase 4: Reply Detection & Analytics
- ✅ Phase 5: Future Enhancements (3 delivered)
- ⏳ Remaining roadmap: CRM sync, LinkedIn, WhatsApp/SMS, Sheets, scheduling, monitoring

### Medium-term (1-2 Months)
- Phase 4: Reply Detection & Analytics
- Testing & Bug Fixes
- Documentation

### Long-term (3+ Months)
- Phase 5: Future Enhancements
- CRM Integrations
- Advanced Features

---

## 📝 Notes

- All API endpoints require authentication (JWT)
- All sensitive data must be encrypted at rest
- All external API keys in environment variables
- Crawler must respect robots.txt and rate limits
- Email sending requires human approval
- All unsubscribe requests honored immediately
- Audit logs for all compliance-related actions

---

**End of Development Plan**

Core roadmap complete. Optional next steps: remaining Phase 5 enhancements, production deployment (OpenTofu plan), MariaDB upgrade
