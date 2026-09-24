# DEVELOPMENT.md — build history of SmartReach AI

Every iteration the project has been through, what each one delivered, and the
lessons that shaped how we build and deploy now. Ops/live-runbook content lives
in [DEPLOYMENT.md](DEPLOYMENT.md); this file is the story and the record.

Timeline at a glance:

| When | Milestone |
|---|---|
| Aug 2026 | Iterations 1.0-1.2: foundation (auth, campaigns, frontend) |
| 2026-08-18 | Iteration 1.3: lead system (model, API, UI) |
| 2026-08-26 → 09-11 | CI/CD + staging VM: pipeline, then the hardening week |
| 2026-08-31 | Iteration 1.4: search & discovery |
| 2026-09-02 | Iteration 1.5: crawling & extraction |
| 2026-09-03 | Iteration 1.6: export — Phase 1 MVP complete |
| 2026-09-08 | Phase 2: AI qualification + personalized email generation |
| 2026-09-09 | Phase 3: email sending with human approval |
| 2026-09-10 | Phase 4: reply detection + analytics; Phase 5: follow-ups, assistant, intent |
| 2026-09-14 | Admin panel; ensure_schema self-applying columns; manual schema scripts; Research Again |
| Sep 2026 | Search provider: SerpAPI (Google CSE blocked account-wide) |
| 2026-09-17 → 09-20 | Production on EC2; real domains wired |
| 2026-09-20 | All deploys made manual + branch-pinned |
| 2026-09-21 | Staging data moved to prod |
| 2026-09-22 | Mailbox: real inbox, threads, reply matching |
| 2026-09-23 | Leads workbench + manual emailing + mailbox compose; prod pull-only lesson |
| 2026-09-24 | Repo cleanup: docs consolidated (this file, DEPLOYMENT.md, README.md) |

---

## Iterations 1.0-1.2 — Foundation (Aug 2026)

- Repo scaffold from the original plan: FastAPI backend, Next.js 14 frontend,
  Celery + Redis, SQLAlchemy models.
- **Auth**: JWT access/refresh, bcrypt hashing, register/login/refresh/me.
- **Campaign system**: CRUD, per-user ownership, keywords (5-10 per campaign),
  status lifecycle (draft → researching → ready → active → paused → completed).
- **Frontend**: app router pages, `useAuth` hook, AppShell with sidebar,
  login/register/campaigns pages.
- Cleanup of the original scaffold's dead artifacts (a workflow file named
  `docker-deployyml` that never ran, duplicate `useAuth` implementations,
  missing Suspense boundaries around `useSearchParams` that broke prerender).
- Backend reformatted with black/isort (line length 100) so future CI gates
  pass from day one.

## Iteration 1.3 — Lead system (2026-08-18)

- `leads` table + model, full CRUD API (`/api/v1/leads`) scoped to the owner.
- Lead status pipeline: new → researching → qualified → review → approved →
  scheduled → sent → replied → interested / rejected, plus
  `do_not_contact`.
- Frontend: leads list per campaign, lead detail page, approve/reject,
  `?campaign_id=` deep links.

## CI/CD + staging — first pass (2026-08-26 → 08-28)

- **User decisions that still stand**: minimal pipeline (no PR checks, no
  Dependabot — it opened 14 PRs on day one and was removed, no security
  scanning, no quality jobs); staging = Ubuntu VM on the local hypervisor;
  single compose file (`docker-compose.yml` IS staging).
- One workflow → GHCR images tagged `sha-<7>` + latest → deploy job on a
  self-hosted runner installed on the VM (192.168.1.30, LAN-only).
- `NEXT_PUBLIC_API_URL` as a repo variable, baked at build time.
- **Lockfile lesson (cost 3 failed CI runs)**: the image is
  `node:24-alpine` (musl); Windows-regenerated lockfiles lack the
  `@emnapi/*` wasm fallbacks → `npm ci` fails in Docker while passing on
  Windows. Fix + verify with
  `npx -y npm@11.19.0 (install --package-lock-only|ci --dry-run) --os=linux --cpu=x64 --libc=musl`.
  Any local `npm install` re-clobbers the lock — regenerate before push.

## Iteration 1.4 — Search & discovery (2026-08-31)

- Multi-provider search agent (`backend/app/integrations/`): shared
  `SearchProvider` base with retrying HTTP + `extract_domain()`; Bing Web
  Search v7 (hosted API retired by Microsoft Aug 2025), Google Programmable
  Search, SerpAPI.
- SerpAPI-style pagination support (`start` offset) — used later by Research
  Again.
- Campaign research pipeline: Celery task fan-out per keyword, live progress
  tracking in the UI, `research_results` rows with dedupe per campaign.

## Iteration 1.5 — Crawling & extraction (2026-09-02)

- `backend/app/crawlers/`: RFC 9309-style robots.txt handler with caching and
  conservative failure policy; contact-page finder scoring same-domain links;
  polite fetcher (rate limits, timeouts).
- Contact extraction (emails, phones, names, social links) → automatic lead
  creation with `DuplicateDetector` blocking dupes per campaign.
- Lead enrichment: `lead_score` inputs, contact URL / source URL provenance.

## Iteration 1.6 — Export & Phase 1 MVP complete (2026-09-03)

- Export service: CSV (UTF-8 BOM, Excel-safe), Excel, JSON — column order per
  the plan spec + Keyword/Status; `MAX_EXPORT_SIZE` guard; ExportButton UI.
- Campaign statistics endpoints (totals, statuses, discovery funnel).
- **Phase 1 MVP end-to-end**: campaign → search → crawl → leads → export.

## Phase 2 — AI qualification & email generation (2026-09-08)

- AI provider abstraction (`LLMClient`, `get_ai_client()` factory): auto picks
  the first configured provider — Anthropic, then OpenAI, then Gemini;
  `AIProviderError` uniformly.
- Lead qualification: score + reasoning per lead; personalized email draft
  generation; drafts stored on the lead, editable before approval.
- Everything routed through human review — the AI never sends.

## Phase 3 — Email sending with human approval (2026-09-09)

- `emails` table (EmailLog): one row per send attempt — to/from, subject,
  body, status sent/failed/bounced, provider, error, message-id, unsubscribe
  token, sent_at. The full audit trail every later feature reuses.
- SMTP client with per-user configurable identity; campaign bulk send gated on
  explicit approval.
- Compliance machinery born here: suppression list, do-not-contact,
  per-user daily/hourly limits, per-lead cooldown, unsubscribe footer +
  one-click unsubscribe URL.

## Phase 4 — Reply detection & analytics (2026-09-10)

- `replies` table: campaign/lead refs, from/subject/body, AI category +
  summary, read flag, thread reference (unique — the dedupe key).
- IMAP polling worker fetches the inbox; AI classifies each reply
  (interested / not interested / unsubscribe / OOO / etc.) and updates lead
  status automatically.
- Reply inbox page, reply analytics (totals, reply rate, unread).

## Phase 5 — Selected enhancements (2026-09-10)

- **Follow-up sequences**: silent leads (status `sent`, no reply, older than
  `FOLLOW_UP_AFTER_DAYS`, under `FOLLOW_UP_MAX_COUNT`) get AI-drafted
  follow-ups through the same approval flow; Celery beat drives eligibility.
- **AI sales assistant**: chat over your campaigns/leads with tool access.
- **Lead intent detection** from reply text feeding the category/status.

## Hardening week — making staging deployable (2026-09-10 → 09-11)

The first staging deploys kept failing; reproducing on the laptop against
`mariadb:10.1.48` found the trio:

1. **Import-time crash**: `assistant_service` built its AI client at module
   import → whole API crash-looped when no AI key was configured. Rule since:
   no env-dependent raises at import; services tolerate missing integrations
   and fail per-request.
2. **Silent no-op entrypoint**: `docker-entrypoint.sh` called async
   `create_tables()` without `asyncio.run` — printed success, created
   nothing. Now awaited + verified, exits 1 if tables are still missing.
3. **MariaDB 10.1 + utf8mb4 = 767-byte index limit** → every indexed string
   column capped at 191 chars (rationale: MARIADB_10.1_COMPATIBILITY.md).

Then the big one (2026-09-11): every deploy failed with
`1045 Access denied for 'leadgen_user'`. Root cause: the MariaDB image only
applies `MYSQL_USER`/`MYSQL_PASSWORD` on an EMPTY volume — the staging volume
kept its day-one credentials no matter what `.staging.env` said, while the old
`mysqladmin ping` healthcheck false-reported healthy. Fixes:

- db healthcheck performs a real login (`mysql -u $MYSQL_USER -p... -e 'SELECT 1'`).
- Entrypoint's required-table list derived from `Base.metadata`, not a
  hardcoded 7-table list.
- One-time `RESET_STAGING_DB` repo variable → deploy wipes and re-initializes
  the volume from current env. Performed once; staging went green and stayed up.

## Admin panel day (2026-09-14) — four deliveries

1. **Admin panel** (`/admin`, Overview / Users / Billing / System;
   `/api/v1/admin/*` behind router-level `get_current_admin`). User decisions:
   billing is manual (plan/status/notes + auto usage + key-presence flags), no
   payment gateway in v1; roles stay admin/user. Guards: no
   self-demote/deactivate/delete; cannot demote/deactivate/delete the last
   active admin; delete cascades with counts + typed-email double confirm;
   System tab returns key-presence booleans only, never values.
   `promote_admin.py` bootstraps the first admin (no "first user is admin"
   magic).
2. **`ensure_schema` — self-applying columns**. The panel added 3 users
   columns and broke staging login ("Unknown column users.plan"): Pydantic
   defaults do NOT protect a deploy where the ORM is ahead of the DB —
   SQLAlchemy SELECTs every mapped column. Fix: the entrypoint now diffs ORM
   columns vs the live DB and auto-runs `ALTER TABLE ... ADD COLUMN`
   (dialect-agnostic; NOT NULL columns need `server_default` on the model;
   failures log the exact statement; new-column indexes stay manual).
   Verified live: dropped billing columns, restarted, watched it heal.
3. **Manual schema scripts** as the fallback if the entrypoint cannot run:
   `database/schema_full.sql` (generated from ORM metadata by
   `generate_schema_sql.py` — MySQL-dialect DDL valid on MariaDB too;
   idempotent via IF NOT EXISTS + inline KEY clauses) +
   `database/incremental/*.sql` (guarded, re-runnable ALTERs). Verified on
   scratch DBs against MariaDB 10.1: generated SQL == ORM exactly; incremental
   twice idempotent.
4. **Research Again**: re-run research to find MORE sites — per-keyword offset
   = count of existing rows (SerpAPI `start` pagination), dedupe keeps only
   new domains, prior campaign status preserved across the run (restored on
   success AND failure). Pure code, no schema change.

Also that week: **entrypoint quoting lesson** — the entrypoint's python block
lives inside `python -c "..."`; a comment containing literal double quotes
truncated the program → SyntaxError → crash-loop. Rule: no double quotes
inside that block, and verify by RUNNING the entrypoint locally
(`bash docker-entrypoint.sh true`), not just `bash -n`.

## Search provider switch — SerpAPI (Sep 2026)

Google Programmable Search started returning 403 account-wide; Bing's hosted
API is retired. **SerpAPI is the active provider** (`SERPAPI_KEY`);
multi-provider architecture made the switch a config change, not a rewrite.

## Production on EC2 (2026-09-17; real domains 2026-09-20)

- Target: the existing AWS EC2 that already serves medidatalab.com (Ubuntu,
  nginx + Let's Encrypt already there). App on subdomains:
  `https://reachpulse.medidatalab.com` / `https://api.medidatalab.com`.
- `docker-compose.prod.yml`: **pull-only** (no build sections), images
  `prod-<sha7>` + `prod-latest` from GHCR; frontend/backend/flower bind
  127.0.0.1 only, db (mysql:8.0)/redis have no ports; real-auth healthcheck;
  everything `restart: unless-stopped`.
- `ci-cd-prod.yml`: manual dispatch, optional `image_tag` input for rollback;
  frontend build requires the `production` GitHub Environment variable
  `NEXT_PUBLIC_API_URL` (environment variables override repo variables).
- Full runbook delivered (nginx vhosts, certbot, DNS + Elastic IP, nightly
  backups → keep-7 + S3, SPF/DKIM/DMARC, uptime monitor, staging→prod
  import). Secrets live in `/opt/smart-reach-ai-prod/.prod.env` on the EC2.
- Compose interpolation gotcha: `docker compose config` on the laptop reads
  the root `.env` for variable substitution — `env_file:` does NOT feed
  interpolation. That is why deploy jobs `set -a; . ./.staging.env; set +a`.

## Deploys made manual + branch-pinned (2026-09-20)

- Push triggers removed from both workflows. Staging ("Build and Deploy")
  always builds+deploys the head of the **staging branch**; prod
  ("Deploy to Production") always builds+deploys **main**. A `resolve` job
  computes the short sha once; every checkout passes an explicit `ref`.
  Rollback overrides via the `image_tag` input (prod).
- Rationale: the user is a single developer — "Run workflow" is the approval
  gate; nothing ships because a branch moved.

## Staging → prod data move (2026-09-21)

- Dump staging as the APP user (root's password drifts on old volumes —
  the second 1045 lesson), `scp` hop via the laptop, import on the EC2 with
  writers stopped, `FLUSHALL` redis, verify row counts, promote admin.
- SECRET_KEY/ENCRYPTION_KEY aligned first so staged encrypted credentials
  decrypt on prod. Full steps: DEPLOYMENT.md §5.8.

## Mailbox (2026-09-22)

- Real inbox experience at `/replies`: threaded conversations per lead (the
  thread reference introduced in Phase 4 becomes the grouping key), unread
  badge in the sidebar, "Check mailbox now" manual IMAP poll.
- Replies from a lead land in the same thread as the outreach email that
  triggered them (message-id / in-reply-to matching).
- Manual reply sending from a thread reuses the Phase 3 compliance machinery
  (suppression, limits via policy decision, unsubscribe) and logs an EmailLog
  row so threading and analytics keep working. Sender identity chain:
  explicit from → last outbound from for that lead → configured SMTP user.

## Leads workbench + manual emailing + compose (2026-09-23)

- **Leads becomes a first-class sidebar page** (between Dashboard and
  Campaigns) showing every lead across campaigns: campaign filter, status
  pills, manual create, edit/reassign to another campaign, export,
  one-off "✉ Email" per row. Campaign pages deep-link with
  `?campaign_id=`. The dashboard stays overview-only.
- **`POST /leads/{id}/email`**: guards (ownership, has email, DNC,
  suppression, SMTP configured) then sends immediately with the standard
  unsubscribe footer, logs EmailLog(status=sent), bumps
  emails_sent/last_emailed_at, sets status "sent" only from early stages —
  never downgrades replied/interested. **No cooldown by design** — a human
  clicked send. SMTP failures log EmailLog(status=failed) + 502.
- **Mailbox Compose**: pick a lead (optionally filtered by campaign) or type
  a fresh address. Fresh address auto-creates a lead under a chosen campaign
  (user's explicit choice; EmailLog.lead_id/campaign_id are NOT NULL, so
  every sent email needs a lead — client-side createLead→emailLead keeps
  that invariant without a schema change), then sends. Errors after
  auto-create point to the Leads tab where the lead now exists.
- Verified with `npx tsc --noEmit` (the CI gate; IDE diagnostics can be
  stale) and py_compile/import checks.

## Prod pull-only lesson (2026-09-23)

The mailbox release did not appear on prod after the usual
`git pull` + `docker compose up -d`. Root cause: prod compose is pull-only
and `up -d` reuses existing local images — it never pulls. `git pull` only
updates the checkout, which containers do not read. The reliable manual flow
(§5.3 of DEPLOYMENT.md): run the build workflow, then
`docker compose ... pull` BEFORE `up -d --remove-orphans`, with
`grep IMAGE_TAG .prod.env` checked for a stale pin. `SCHEMA:` lines in the
backend log confirm a new image booted.

## Docs consolidation (2026-09-24)

- 20+ scattered/obsolete docs (scaffold guides, per-iteration reports,
  deploy scripts from Iteration-1.3 era) consolidated into **README.md**
  (what it is), **DEPLOYMENT.md** (how to run it everywhere + schema
  playbook) and this file (what happened). Legacy scripts removed:
  `deploy.sh/.bat`, `run-migrations.sh/.bat`, `backend/migrate.py`,
  one-off fix scripts, stale env templates. Alembic files 001-009 kept as
  convention (not wired into deploys — §6.2 of DEPLOYMENT.md).

---

## Standing lessons (the short list)

1. MariaDB volumes keep day-one credentials — env edits never reach them;
   healthchecks must do real logins.
2. Schema converges via create_all + ensure_columns; NOT NULL needs
   `server_default`; indexes on new columns are manual. Alembic exists but is
   not wired.
3. Frontend lockfiles: regenerate for musl after any Windows `npm install`.
4. `NEXT_PUBLIC_API_URL` (and everything `NEXT_PUBLIC_*`) is baked at build
   time — changing it means rebuilding the image.
5. Prod never deploys from `up -d` alone — always pull first (pull-only
   compose).
6. All deploys are manual workflow runs; staging tracks the staging branch,
   prod tracks main.
7. Verify like production runs: run the entrypoint, `npx tsc --noEmit`,
   drop-a-column-and-restart drills — not just lint/parse checks.
