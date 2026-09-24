# SmartReach AI (ReachPulse)

AI-powered B2B lead generation and cold-outreach platform: discovers potential
clients via web search, crawls their sites for public contact info, qualifies
and scores leads with AI, drafts personalized emails for human approval, sends
them with full compliance machinery, detects replies, and keeps the whole
conversation in one mailbox.

**Live (production):** https://reachpulse.medidatalab.com ·
API: https://api.medidatalab.com

## How it works

```
Campaign (5-10 keywords)
  -> Web search (SerpAPI; multi-provider architecture)
  -> Polite crawl (robots.txt-compliant, contact-page finder)
  -> Leads with contact info + provenance (deduped per campaign)
  -> AI qualification: score + reasoning (Anthropic / OpenAI / Gemini)
  -> AI-drafted personalized emails -> HUMAN APPROVAL
  -> SMTP send with unsubscribe link, suppression list, rate limits
  -> IMAP reply detection -> AI classification -> status automation
  -> Threaded mailbox, follow-up sequences, analytics, CSV/Excel/JSON export
```

## Feature highlights

- **Campaigns & research**: keyword-driven discovery with live progress;
  "Research Again" re-runs search with pagination to find *more* sites.
- **Leads workbench**: all leads across campaigns — manual create, campaign
  re-assignment, one-off manual emailing, status pipeline, export.
- **Approval-first sending**: nothing ships without a human; bulk sends and
  single/manual sends both log an auditable EmailLog row.
- **Mailbox**: threaded conversations, unread badges, compose (pick a lead or
  auto-create one from a fresh address), manual IMAP poll.
- **Replies**: AI-classified (interested / not-interested / unsubscribe / …),
  automatic lead status updates, reply analytics.
- **Follow-ups**: timed AI-drafted follow-ups for silent leads, still
  approval-gated.
- **AI assistant**: chat over your own campaigns/leads data.
- **Compliance**: suppression list, do-not-contact, per-user rate limits,
  unsubscribe footer + one-click unsubscribe, robots.txt compliance.
- **Admin panel**: users, manual billing (plan/status/notes), usage,
  key-presence checks, system overview; guarded admin routes + bootstrap CLI.

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (app router), React, TypeScript, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | MariaDB 10.1 (staging) / MySQL 8.0 (prod) — schema is engine-agnostic by design |
| Queue | Celery + Redis (worker, beat scheduler, Flower) |
| AI | Anthropic Claude, OpenAI, Gemini — first configured provider wins |
| Search | SerpAPI (active), pluggable: Google Programmable Search, Bing |
| Email | SMTP sending + IMAP polling; per-user sender identity |
| Images | GHCR: `ghcr.io/rimiag/smart-reach-ai-{backend,frontend}` (`sha-<7>` staging / `prod-<sha7>` prod) |
| CI/CD | GitHub Actions, manual dispatch only, branch-pinned (staging branch / main), self-hosted deploy runner |

## Quick start (local, no app containers)

```bash
# 1. Database + Redis only:
docker-compose up -d db redis

# 2. Backend (Python 3.11+):
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env                               # fill DATABASE_URL + SECRET_KEY
uvicorn app.main:app --reload --port 8000            # http://localhost:8000/docs
#   extra terminals: celery -A app.tasks.celery_app worker / beat

# 3. Frontend (Node 20+):
cd frontend
npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm run dev                                          # http://localhost:3000
```

Tables are created automatically on first boot (ORM models are the source of
truth). Register, then `python promote_admin.py <email>` for admin.
Full details incl. Celery and env keys: [DEPLOYMENT.md](DEPLOYMENT.md) §3.

## Deployments

| Environment | How |
|---|---|
| **Staging** — Ubuntu VM `192.168.1.30`, MariaDB 10.1 | `git push origin main:staging`, then Actions → **Build and Deploy** → Run workflow |
| **Production** — EC2, MySQL 8, behind your nginx + certbot | Actions → **Deploy to Production** (builds from `main`), then on the EC2: `docker compose --env-file .prod.env -f docker-compose.prod.yml pull` **before** `up -d --remove-orphans` (pull-only compose — `up -d` alone reuses stale images) |

Everything (one-time setup, env-file mapping, schema/migrations playbook,
backups, rollback, troubleshooting): [DEPLOYMENT.md](DEPLOYMENT.md).

## Repository layout

```
backend/
  app/api/v1/          # REST endpoints (auth, campaigns, leads, mailbox, admin, ...)
  app/models/          # SQLAlchemy ORM models - the schema source of truth
  app/services/        # business logic (email, research, replies, exports, ...)
  app/integrations/    # AI providers, search providers, SMTP/IMAP
  app/crawlers/        # robots.txt, page finder, polite fetcher, extraction
  app/tasks/           # Celery app + tasks
  app/db/ensure_schema.py   # self-applying column ADDs on boot
  docker-entrypoint.sh # wait-for-db, create tables, ensure columns, verify
  alembic/versions/    # 001-009 (convention/history - NOT wired into deploys)
  promote_admin.py     # admin bootstrap CLI
  generate_schema_sql.py    # regenerates database/schema_full.sql from ORM
frontend/
  src/app/             # dashboard, leads, campaigns, replies (mailbox),
                       #   analytics, assistant, admin pages
  src/components/      # AppShell, modals (lead form, manual email, compose), ...
  src/lib/api.ts       # typed axios client
database/              # schema_full.sql + incremental/ (manual fallback) + README
docker-compose.yml     # staging stack (also runs local db+redis)
docker-compose.prod.yml# prod stack (pull-only)
.github/workflows/     # ci-cd.yml (staging), ci-cd-prod.yml (prod)
```

## Configuration

Env templates: `backend/.env.example` (local/staging keys),
`.staging.env.example` (staging VM), `.prod.env.example` (prod EC2).
Key groups: security (`SECRET_KEY`, `ENCRYPTION_KEY`), database
(`DATABASE_URL` or `DB_*`), Redis/Celery, `SERPAPI_KEY`, AI keys (any one of
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`), `SMTP_*` to send,
`IMAP_*` for reply detection, follow-up tuning. Never commit real values.

## Database schema policy (short version)

ORM models are the single source of truth. Every backend container boot:
waits for db → creates missing **tables** → auto-adds missing **columns**
(`ALTER TABLE ... ADD COLUMN`) → verifies, failing loudly otherwise.
Consequences:

- Adding a nullable column = change the model and deploy. Nothing else.
- NOT NULL columns need `server_default` on the model.
- Type changes / drops / new-column indexes stay manual
  (`database/` scripts are the guarded fallback).
- Alembic files are kept as history but are **not** wired into deploys.

Full playbook (decision table, manual scripts, traps):
[DEPLOYMENT.md](DEPLOYMENT.md) §6 and [database/README.md](database/README.md).

## Development workflow

- **Type-check gate**: `cd frontend && npx tsc --noEmit` (CI runs it inside
  the Docker build; IDE diagnostics can be stale — tsc is the truth).
- **Backend style**: black + isort, line length 100.
- **Lockfile trap**: the frontend image is alpine/musl — after any local
  `npm install`, regenerate for linux:
  `npx -y npm@11.19.0 install --package-lock-only --os=linux --cpu=x64 --libc=musl`.
- **Deploys are manual**: pushing never deploys anything. Staging workflow
  builds the staging branch; prod workflow builds main.
- Secrets live only in env files on the machines that use them
  (`backend/.env`, VM `.staging.env`, EC2 `.prod.env`) — all gitignored.

## Documentation

| Doc | Read it for |
|---|---|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Local + staging + prod deployment, env files, schema/migrations playbook, backups, rollback, troubleshooting |
| [DEVELOPMENT.md](DEVELOPMENT.md) | The full build history: every iteration, feature, decision and lesson |
| [database/README.md](database/README.md) | Manual schema scripts: usage, verification, full recovery |
| [MARIADB_10.1_COMPATIBILITY.md](MARIADB_10.1_COMPATIBILITY.md) | Why indexed strings are capped at 191 chars |

## License

Proprietary — all rights reserved.
