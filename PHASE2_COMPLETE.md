# Phase 2 Complete - AI Qualification & Email Generation

**Date:** 2026-09-08
**Status:** ✅ PHASE 2 COMPLETE (Phases 1-2 done)

---

## What Was Built

### 1. AI Provider Abstraction (`backend/app/integrations/`)
- **`ai_base.py`** - `LLMClient` interface (`complete(system, user) -> text`),
  `AIProviderError`, and `get_ai_client()` factory (`ai_provider=auto` picks
  the first configured provider: Anthropic, then OpenAI, then Gemini).
- **`anthropic_client.py`** - Anthropic messages API via SDK 1.x.
  Defaults: `claude-haiku-4-5` (bulk qualification), `claude-sonnet-5`
  (email writing).
- **`openai_client.py`** - OpenAI chat completions.
  Defaults: `gpt-4o-mini` / `gpt-4o`.
- **`gemini_client.py`** - Google Gemini via its OpenAI-compatible endpoint.
  Free tier (aistudio.google.com/apikey, no credit card): `gemini-2.5-flash`.
  Recommended for development.
- SDKs bumped: `anthropic==1.4.0`, `openai==3.8.0`.

### 2. Qualification Agent (`backend/app/agents/qualification_agent.py`)
- Scores each lead 0-100 with reasoning and a category label, using the
  campaign keywords + lead contact facts.
- Robust `SCORE:/REASONING:/CATEGORY:` parsing (tolerates noise, clamps
  0-100, raises `QualificationParseError` when unusable).
- Qualified leads: `lead_score`, `ai_reasoning` (`[category] reasoning`),
  `status: new -> review`, `qualified_at` set.

### 3. Email Generation Agent (`backend/app/agents/email_agent.py`)
- Drafts a personalized subject + body (90-150 words) per lead from
  verified personalization facts only - the prompt forbids invention.
- `{{SENDER_NAME}}` / `{{SENDER_COMPANY}}` stay as placeholders for Phase 3.
- Stored on `lead.generated_email` as `Subject: ...\n\n body`.

### 4. Template + Personalization Services
- **`template_service.py`** - three style variants (professional,
  short_direct, value_first) rotated round-robin per lead;
  `{{VAR|default}}` rendering with unknown placeholders preserved.
- **`personalization_service.py`** - builds the verified-facts context from
  lead + campaign for prompts.

### 5. Pipeline + Tasks
- Research pipeline is now **search → crawl → AI qualification → finalize**.
  With `ai_auto_qualify=True` (default) and no provider key, qualification
  is skipped silently and leads stay `new` (never a run failure).
- `app/tasks/qualify_tasks.py` (`qualify_campaign`, "ai" queue) and
  `app/tasks/email_tasks.py` (`generate_campaign_emails`) - both with 2h
  limits, per-lead failure containment, progress-tracker steps.
- **Celery registration fix**: task modules are now imported explicitly in
  `celery_app.py` - autodiscovery never registered them in the worker
  (latent bug that would have broken queue-based research).

### 6. API Endpoints
| Endpoint | Purpose |
|----------|---------|
| `POST /campaigns/{id}/qualify` | Queue AI qualification of `new` leads (400 if no provider) |
| `POST /campaigns/{id}/generate-emails` | Queue email drafts for review-ready leads |
| `POST /leads/{id}/qualify` | Synchronous single-lead qualification |
| `POST /leads/{id}/regenerate` | Synchronous single-lead draft (re)generation |

### 7. Frontend
- **Review Queue** (`/leads/review?campaign_id=`) - score-sorted decision
  queue with AI reasoning, expandable email draft preview, approve/reject.
- **Lead detail** - Qualify with AI / Generate Email buttons, AI
  qualification card, email draft card with regenerate.
- **Campaign detail** - Qualify / Generate Emails / Review Queue actions.

---

## ✅ Verification Performed

- Unit checks: qualification + email response parsing (valid, malformed,
  clamping), template round-robin and `{{VAR|default}}` rendering
- Service E2E (real MariaDB, fake AI client): `new → review` transitions with
  scores, idempotent re-runs, draft skip-existing vs regenerate modes,
  placeholder preservation
- Endpoint tests: 400 fail-fast without provider, per-lead qualify/regenerate
  with fake provider, ownership via auth override
- Frontend `next build`; all 5 Celery tasks registered; DB left clean

---

## 🔧 To Enable

Set one of (backend `.env` locally / `.staging.env` on staging):

```env
ANTHROPIC_API_KEY=sk-ant-...    # recommended (haiku-4-5 + sonnet-5 defaults)
# or
OPENAI_API_KEY=sk-...
```

Restart the backend. New research runs then qualify automatically; existing
`new` leads can be qualified via the campaign page button. Cost note:
qualification uses Haiku-class models (~$1/$5 per 1M tokens) - a 17-lead
campaign costs a fraction of a cent per run.

---

## 🔜 What's Next: Phase 3

**Email Sending & Human Approval** - SMTP/SES/Gmail integrations, sending
limits, scheduler, suppression list, approval workflow UI. The
`{{SENDER_*}}` placeholders and approval-only drafts were designed for it.

---

**End of Phase 2**
