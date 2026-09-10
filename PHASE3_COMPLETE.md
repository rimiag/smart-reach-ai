# Phase 3 Complete - Email Sending with Human Approval

**Date:** 2026-09-09
**Status:** ✅ PHASE 3 COMPLETE (Phases 1-3 done)

---

## What Was Built

### 1. Send Log (`backend/app/models/email_log.py` + migration 003)
`emails` table: one row per send attempt (to/from, subject, body, status
sent/failed/bounced, provider, error, message-id, unsubscribe token, sent_at).
Full audit trail for every outreach email.

### 2. Suppression List (`backend/app/models/suppression.py`)
`suppressions` table: emails that must never be contacted (unsubscribed /
bounced / manual), unique per user. Checked before **every** send.

### 3. SMTP Provider (`backend/app/integrations/smtp_client.py`)
aiosmtplib + STARTTLS; works with Gmail app passwords, Outlook, or any SMTP
relay. Configured via `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` /
`SMTP_PASSWORD` (+ optional `SMTP_FROM_EMAIL`). SES / Gmail API / Graph can be
added later behind the same interface.

### 4. Sending Guardrails (`backend/app/core/rate_limits.py`)
- 50 emails/day, 10 emails/hour (default) - a run **stops politely** at the
  limit and can be resumed by clicking send again
- 7-day per-lead cooldown
- configurable pacing delay between sends

### 5. Email Service (`backend/app/services/email_service.py`)
`send_campaign()` per approved lead: suppression check → cooldown check →
volume limit check → final rendering (sender placeholders filled, unsubscribe
footer appended) → SMTP send → audit row → lead `sent` / `emails_sent++` /
`last_emailed_at`. Failures are per-lead contained and logged.

### 6. Approval Workflow
- `POST /campaigns/{id}/approve-all` - one-click approve of reviewed leads
  with drafts
- `POST /campaigns/{id}/send` - explicit human send with sender identity
  (name/company/from/reply-to, persisted in campaign settings); only
  `approved` leads with drafts are sent
- **Review & Send page** (`/campaigns/[id]/approve`): sender identity form,
  score-sorted send queue, confirmation checkbox, live progress polling

### 7. Compliance
- **One-click unsubscribe**: every email footer carries
  `/api/v1/unsubscribe/{lead_id}/{token}` (deterministic per-lead token, no
  auth, invalid tokens rejected). A click suppresses the email, marks the lead
  `do_not_contact` + `unsubscribed`.
- Suppression CRUD: `GET/POST/DELETE /api/v1/suppression`
- Send log: `GET /api/v1/emails?campaign_id=`

---

## Verification Performed

- Unit: unsubscribe token determinism, final rendering (placeholder fill +
  unsubscribe footer), limits wiring - passed
- Service E2E with a fake SMTP transport against real MariaDB: 2 sent with
  correct substitution, 1 suppression skip, 1 cooldown skip, audit rows and
  lead transitions verified, non-approved leads untouched - passed
- Endpoint tests (TestClient + auth override): 400 SMTP-unconfigured,
  approve-all, send dispatch, send-log listing, unsubscribe valid/invalid
  token + suppression + lead marking - passed
- Frontend tsc - passed; DB left clean (no test fixtures)

---

## To Enable Sending

Set SMTP settings (backend `.env` locally, `.staging.env` on staging):

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@yourcompany.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=you@yourcompany.com
```

Gmail: use an **App Password** (Google Account → Security → 2FA → App
passwords). Then: campaign → **📨 Review & Send** → fill sender identity →
confirm → Start sending.

---

## Next: Phase 4 - Reply Detection & Analytics

IMAP/Graph reply polling, AI reply classification, bounce handling (feedback
into the suppression list), and the analytics dashboard.

---

**End of Phase 3**
