# Phase 5 - Selected Enhancements Delivered

**Date:** 2026-09-10
**Status:** ✅ 3 of 11 enhancements delivered (follow-up sequences, AI sales assistant, lead intent detection)

---

## 1. Follow-up Sequences (High priority)

Silent leads automatically get AI-drafted follow-ups, routed through the same
human-approval flow as everything else.

**Eligibility** (per lead): status `sent` · no reply received · last email
older than `follow_up_after_days` (default 4) · fewer than
`follow_up_max_count` (default 2) follow-ups already drafted.

**Flow:** daily Celery beat sweep (or on-demand
`POST /campaigns/{id}/generate-followups`) → AI drafts a shorter, polite
follow-up into `generated_email` → lead returns to `review` → you approve in
Review & Send as usual. `follow_up_count` on the lead tracks the sequence
position; already-sent emails are never re-sent.

**Config:** `follow_up_enabled`, `follow_up_after_days`, `follow_up_max_count`.

---

## 2. AI Sales Assistant

`POST /api/v1/assistant/ask` + `/assistant` chat page.

Ask natural-language questions about your own data — grounded **strictly** in
your database content (volume metrics, campaigns, top leads by score, recent
replies). The assistant states plainly when the data doesn't contain an
answer; it never invents numbers.

---

## 3. Lead Intent Detection

`backend/app/services/intent_service.py` — during qualification, the lead's
homepage is fetched and scanned for buying signals:

- **hiring** (careers/we're hiring)
- **demo_or_trial_cta** (book a demo, free trial)
- **growth** (funding, expansion)
- **buying_signals** (looking for / seeking a partner)
- **mentions:<keyword>** — campaign keywords appearing on their site

Signals sharpen the AI qualification prompt and appear in the lead's
`ai_reasoning` (`| Signals: ...`). Gated by `intent_detection_enabled`
(default on); fetch failures never break scoring.

---

## Remaining Phase 5 Roadmap (need external accounts/credentials)

- **CRM sync** (HubSpot/Salesforce) — needs CRM account + API keys
- **Google Sheets sync** — needs Google OAuth app
- **LinkedIn research** — API access closed to new apps
- **WhatsApp / SMS outreach** — needs Twilio/WhatsApp Business
- **Meeting scheduling** — Calendly integration
- **Change/competitor monitoring** — crawler-based, no external deps

---

## Verification Performed

- Unit: intent signal extraction on canned page text - passed
- Follow-up sweep E2E with fake AI + real MariaDB: eligibility (recently
  emailed excluded, maxed-out excluded), draft → review with counter
  increment, idempotent re-sweeps - passed
- Assistant endpoint (fake AI): grounded answers returned - passed
- Frontend tsc + `next build` - passed; DB left clean

---

**End of Phase 5 (selected scope) — the platform roadmap is delivered.**
