# Staging Deployment Guide — SmartReach AI

The one document for getting code onto staging and keeping it healthy.
Runner/VM bootstrap details live in `CICD_SETUP.md`; this guide covers
configuration, deployment, the database, and troubleshooting.

**Status of this document:** written 2026-09-11, after diagnosing why deploys
were failing (see next section). If staging is broken, start at
[Troubleshooting](#9-troubleshooting).

## 0. TL;DR — get staging green today

Staging deploys were failing with `Access denied for user 'leadgen_user'`
because the MariaDB volume on the VM holds credentials from whenever it was
FIRST initialized; later edits to `.staging.env` never reach the volume.
Fix (staging data is disposable test data):

```bash
# 1. Update the VM's env file (see section 3): same keys as laptop .env,
#    plus the staging-only values (URLs, DB creds).
#    From the hypervisor host:  ssh <vm-user>@192.168.1.30
#    sudo nano /opt/smart-reach-ai-staging/.staging.env

# 2. Arm the one-time DB reset (repo variable):
gh variable set RESET_STAGING_DB -R rimiag/smart-reach-ai --body yes
#    (or: GitHub web UI -> Settings -> Secrets and variables -> Actions ->
#     Variables -> New repository variable, name RESET_STAGING_DB, value yes)

# 3. Push to main (or Actions -> "Build and Deploy" -> Run workflow).
#    The deploy wipes the db volume, re-initializes it with the CURRENT
#    .staging.env, and the app creates all tables itself.

# 4. When the run is green, disarm the reset:
gh variable set RESET_STAGING_DB -R rimiag/smart-reach-ai --body no
```

Then verify with the checklist in section 7.

## 1. How deployment works

```
push to main  (or Actions -> Run workflow)
   |
   +-- [cloud] build backend image  -> ghcr.io/rimiag/smart-reach-ai-backend:sha-<7>
   +-- [cloud] build frontend image -> ghcr.io/rimiag/smart-reach-ai-frontend:sha-<7>
   +-- [on the VM, self-hosted runner]
         copy /opt/smart-reach-ai-staging/.staging.env into checkout
         (optional) wipe db volume if RESET_STAGING_DB=yes
         docker compose pull && docker compose up -d
         poll http://localhost:8000/health + :3000 until healthy
```

- Every image is tagged with the short commit sha it was built from, so the VM
  runs exactly the commit that was pushed. `latest` is also updated.
- The runner dials OUT to GitHub; the VM keeps no inbound internet. Reach the
  app from the hypervisor host browser at `http://192.168.1.30:3000`.
- On failure the workflow now dumps `compose ps`, backend/db logs and VM
  resources into the run log (step "Dump diagnostics on failure") before you
  would otherwise need to SSH in.

## 2. Why deploys were failing (root cause, 2026-09-11)

```
pymysql.err.OperationalError: (1045, "Access denied for user
'leadgen_user'@'172.19.0.4' (using password: YES)")
```

- The MariaDB image only creates `MYSQL_USER` / `MYSQL_PASSWORD` when its data
  volume is EMPTY. The staging volume was initialized long ago; the password in
  the volume is whatever was set on day one, not what is in today's
  `.staging.env`.
- The old db healthcheck (`mysqladmin ping`) reported "healthy" even when
  authentication was broken, so the failure surfaced as a confusing
  backend crash-loop instead of a db error.
- The same volume also predates the utf8mb4 init and the Phase 5
  `leads.follow_up_count` column.

Fixes in place:
- db healthcheck now performs a real login with the app credentials
  (`mysql -u $MYSQL_USER -p... -e 'SELECT 1'`), so credential drift fails the
  deploy at the db, with a clear error, not as a backend crash-loop.
- One-time volume reset wipes the old state (section 5).
- Entrypoint now derives the expected-table list from the ORM models instead
  of a hardcoded list, so new models are never missed.

## 3. Configuration: from laptop `.env` to staging `.staging.env`

The staging VM keeps its env at `/opt/smart-reach-ai-staging/.staging.env`
(gitignored, never committed; template in `.staging.env.example`). The deploy
job copies it into the checkout and sources it. The file must be plain
`KEY=value` lines (no spaces, no quotes) because it is `source`d by the shell.

You asked to reuse the laptop keys - that is exactly right for the
third-party keys and secrets. Three groups:

### 3a. Copy verbatim from laptop `.env` (same key, same value)

| Group | Keys |
|---|---|
| Security | `SECRET_KEY`, `ENCRYPTION_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| Search | `SERPAPI_KEY` |
| AI | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`, `ANTHROPIC_MODEL` |
| Email sending | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_FROM_EMAIL` |
| Reply detection | `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_FOLDER` |
| Follow-ups | `FOLLOW_UP_ENABLED`, `FOLLOW_UP_AFTER_DAYS`, `FOLLOW_UP_MAX_COUNT` |
| Tuning (has sane defaults, copy if you like) | `CELERY_*`, `RATE_LIMIT_*`, `CRAWLER_*`, `DEFAULT_DAILY_EMAIL_LIMIT`, `DEFAULT_HOURLY_EMAIL_LIMIT`, `DEFAULT_EMAILS_PER_LEAD_DAYS`, `DB_POOL_*`, `REDIS_CACHE_TTL`, `MAX_EXPORT_SIZE`, `APP_NAME` |

Notes:
- Reusing `SECRET_KEY` / `ENCRYPTION_KEY` across laptop and staging is fine for
  a single-developer setup. If staging ever becomes externally reachable or
  multi-user, give it its own pair (rotating them just invalidates existing
  sessions and re-encryption of stored credentials).
- Provider keys that are EMPTY on the laptop stay empty on staging: today that
  is `GEMINI_API_KEY` and the `IMAP_*` set. Consequence: the AI assistant and
  reply detection are switched off on staging exactly like on your laptop
  (assistant answers return a clear "no AI provider configured" error). To
  enable later: get the key, add it to BOTH laptop `.env` and the VM's
  `.staging.env`, then redeploy (push or Run workflow).

### 3b. Must be staging-specific values (do NOT copy from laptop)

| Key | Staging value |
|---|---|
| `API_URL` | `http://192.168.1.30:8000` |
| `FRONTEND_URL` | `http://192.168.1.30:3000` |
| `CORS_ORIGINS` | `http://192.168.1.30:3000` (add `http://localhost:3000` only if you also test the local frontend against staging API) |
| `DB_NAME` | `leadgen_db` (or your choice - see the caveat in section 6) |
| `DB_USER` / `DB_PASSWORD` | anything strong; these become the db account ON RESET (section 5). Not in laptop `.env` because the laptop keeps its creds inside `DATABASE_URL`. |
| `MYSQL_ROOT_PASSWORD` | anything strong |

### 3c. Omit - overridden by compose or the pipeline

| Key | Why |
|---|---|
| `DATABASE_URL` | compose builds it as `mariadb+aiomysql://$DB_USER:$DB_PASSWORD@db:3306/$DB_NAME` - container-internal hostname. |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | compose forces `redis://redis:6379/0`. |
| `ENVIRONMENT`, `LOG_LEVEL`, `LOG_FORMAT` | compose forces `staging` / `INFO` / `json`. |
| `NEXT_PUBLIC_API_URL` | NOT an env file key - it is a GitHub repo **variable** baked into the frontend bundle at build time (Settings -> Secrets and variables -> Actions -> Variables; workflow falls back to `http://192.168.1.30:8000`). |
| `IMAGE_TAG` | exported by the pipeline per deploy. |

## 4. Deploying (normal flow)

1. Merge/push to `main`. That is the whole deployment.
2. Watch the run: GitHub -> Actions -> "Build and Deploy".
3. A green run = images pushed AND stack healthy on the VM.
4. Redeploy the same commit without a new push: Actions -> the run -> Re-run
   all jobs; or manually from the Actions tab: Run workflow.

Changing these triggers a rebuild+redeploy too:
- repo variable `NEXT_PUBLIC_API_URL` (frontend bundle) -> push or Run workflow
- VM's `.staging.env` -> just Run workflow (images unchanged, env re-read by
  `docker compose up -d`)

## 5. One-time staging DB reset

Use this when the volume's credentials or schema have drifted from the current
code/env (that is the state staging is in right now). It deletes ALL staging
data - fine while staging holds only test data; do NOT do this once staging
holds anything you care about (use the ALTER approach in section 6 instead).

What it does on the VM during the deploy:

```
docker compose stop db
docker compose rm -f db
docker volume rm smart-reach-ai-staging_mysql_data   # all data gone
# then `up -d` re-initializes from scratch:
#   - MYSQL_DATABASE / MYSQL_USER / MYSQL_PASSWORD created from CURRENT .staging.env
#   - backend/db/init.sql sets utf8mb4 + unicode collation
#   - backend entrypoint creates ALL tables from the ORM models
```

Steps:

1. First make sure `/opt/smart-reach-ai-staging/.staging.env` on the VM is
   correct (section 3) - the reset bakes THOSE values into the fresh volume.
2. Arm it: `gh variable set RESET_STAGING_DB -R rimiag/smart-reach-ai --body yes`
3. Push to main or Actions -> Run workflow.
4. Confirm the run is green and the checklist (section 7) passes.
5. Disarm immediately: `gh variable set RESET_STAGING_DB -R rimiag/smart-reach-ai --body no`
   (the deploy logs a loud warning while it is armed, but do not leave it on -
   any future push would wipe staging data).

After a reset, users must register again (the `users` table is empty).

## 6. Database schema, migrations, and the "will it work on any DB" answer

This is the part that used to cost hours. The rules that make it boring now:

**How tables get created.** The ORM models in `backend/app/models/` are the
single source of truth. Every backend-family container start (backend, worker,
scheduler) runs `docker-entrypoint.sh`, which:

1. waits for the db to accept connections,
2. lists the tables that SHOULD exist - derived from the ORM metadata, not a
   hardcoded list (so a new model is picked up automatically),
3. creates the missing ones with SQLAlchemy `create_all` (only missing tables;
   never alters existing ones),
4. re-verifies and exits 1 (container fails loudly) if anything is still
   missing.

A fresh database therefore always converges to the complete current schema on
any supported engine, with zero manual steps. The Alembic files under
`backend/alembic/versions/` (001-005) exist but are NOT wired into the deploy;
do not rely on them running automatically.

**Version-agnostic by construction.**

- All DDL goes through SQLAlchemy (dialect-generic) - no stored procedures, no
  version-specific SQL, no `init.sql` table dumps. `init.sql` only sets the
  database charset.
- Every indexed string column is capped at 191 chars (utf8mb4 index limit on
  MariaDB 10.1; harmless on anything newer - see
  `MARIADB_10.1_COMPATIBILITY.md`).
- Drivers are `aiomysql`/`pymysql`, which speak to MariaDB and MySQL alike.

Consequence: the same images run against the pinned `mariadb:10.1.48` in
staging compose today and against, say, `mariadb:11.x` or `mysql:8.x` in
production later - you change only the db `image:` line (and, for MySQL, the
`DATABASE_URL` scheme `mariadb+aiomysql` keeps working; `mysql+aiomysql` is
equivalent).

**When you change a model (the decision rule):**

| Situation | What to do |
|---|---|
| Staging, data disposable | One-time reset (section 5). Simplest, always correct. |
| Keep the data, one column/table | Manual ALTER on the VM, e.g. what `005_follow_up_count.py` does: `docker exec -it smart-reach-ai-staging-db-1 mysql -u root -p<MYSQL_ROOT_PASSWORD> leadgen_db -e "ALTER TABLE leads ADD COLUMN follow_up_count INT NOT NULL DEFAULT 0;"` |
| Real data, frequent schema changes | Wire Alembic into the entrypoint (replace the create_all path with `alembic upgrade head`). IMPORTANT for DBs that were built by create_all: run `alembic stamp head` once first, or Alembic will try to re-create existing tables. |

`create_all` never alters existing tables - that is why a model change needs
one of the three rows above.

**Two named traps:**

1. `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` only take effect on an
   EMPTY volume. Changing `.staging.env` DB credentials on an existing volume
   does nothing until you reset the volume or run `ALTER USER` in the db
   container. (This was the 2026-09-11 outage.)
2. `backend/db/init.sql` hardcodes the database name
   (`ALTER DATABASE leadgen_db ...`). If you ever change `DB_NAME`, change
   init.sql to match, or drop the file's ALTER and set the charset in compose.


## 7. Post-deploy verification checklist

From the laptop (hypervisor host network):

```bash
curl http://192.168.1.30:8000/health     # expect 200 with status ok
curl -I http://192.168.1.30:3000         # expect HTTP 200
```

On the VM (SSH from the hypervisor host):

```bash
docker compose ps          # every service Up (healthy) - backend, worker,
                           # scheduler, flower, db, redis, frontend
docker logs --tail 50 smart-reach-ai-staging-backend-1
                           # should show "All required tables exist."
# Prove the schema really converged (fresh reset):
docker exec smart-reach-ai-staging-db-1 mysql -u leadgen_user -p leadgen_db \
  -e "SHOW TABLES; SHOW TABLE STATUS WHERE Name='leads'\G" | grep -iE 'users|campaigns|leads|research|emails|suppressions|replies|Collation'
```

In the browser at `http://192.168.1.30:3000`:

- register a user, log in
- create a campaign, run a search (exercises `SERPAPI_KEY`)
- (if SMTP configured) send a test email
- Celery monitor: `http://192.168.1.30:5555` (flower)

## 8. Rollback

Images are immutable per commit, so rollback is just redeploying an older tag:

- Preferred: Actions -> the older GREEN run -> **Re-run all jobs** (rebuilds are
  cache-hits; the deploy re-pins `IMAGE_TAG` to that sha).
- Manual on the VM: in the runner checkout,
  `export IMAGE_TAG=sha-<old7> && docker compose up -d`.

Note: a rollback moves code back but does NOT roll the database back - if the
newer commit changed the schema via one of the section-6 paths, plan that
before rolling back.

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Deploy fails, backend logs show `Access denied ... (1045)` for `leadgen_user` | Volume credentials drifted from `.staging.env` (section 2). One-time reset (section 5), or keep data: `docker exec -it smart-reach-ai-staging-db-1 mysql -u root -p<root-pw> -e "ALTER USER 'leadgen_user'@'%' IDENTIFIED BY '<pw-from-env>'; FLUSH PRIVILEGES;"` |
| Deploy fails at "db healthcheck" now (used to pass) | The healthcheck now does a real login. It is telling the truth: the db credentials do not match the volume -> same fix as the row above. |
| Backend unhealthy, tables missing in logs | Entrypoint failed to create tables. Read the container log in the "Dump diagnostics" step of the run - it names the exact tables. Common cause: db not actually up when checked, or wrong `DATABASE_URL` interpolation. |
| Deploy job queued forever | Self-hosted runner offline: on the VM `sudo ~/actions-runner/svc.sh status` (restart with `stop`/`start`). |
| Deploy can't pull images from GHCR | Package is private and VM not logged in: `echo <PAT> \| docker login ghcr.io -u rimiag --password-stdin`, or set the `GHCR_PAT` repo secret. |
| `.staging.env is missing` error in deploy | Create `/opt/smart-reach-ai-staging/.staging.env` from `.staging.env.example`. |
| Frontend calls the wrong API host | `NEXT_PUBLIC_API_URL` repo variable missing/wrong at BUILD time. Fix the variable, then Run workflow (rebuild needed - it is baked into the JS bundle). |
| Frontend build fails in CI with `Missing: @emnapi/... from lock file` | Lockfile was regenerated on Windows. In `frontend/`: `npx -y npm@11.19.0 install --package-lock-only --os=linux --cpu=x64 --libc=musl` then commit (see CICD_SETUP.md). |
| Assistant / AI chat returns 400 | No AI provider key configured (`GEMINI_API_KEY` etc. empty). Add to laptop `.env` AND VM `.staging.env`, redeploy. |
| Data reset surprised me | `RESET_STAGING_DB` repo variable was left `yes`. Set it back to `no` (section 5 step 5). |

## 10. Production outlook (when it exists)

Staging is this exact stack; production differs only in degree, not in kind:

- **Database**: swap the `db:` image (e.g. `mariadb:11.x` or managed
  MySQL/Aurora). Code, models and migrations are engine-version-agnostic by
  construction (section 6); the 191-char indexed-column caps stay valid.
- **URLs**: real DNS + HTTPS. `NEXT_PUBLIC_API_URL` and the `API_URL` /
  `FRONTEND_URL` / `CORS_ORIGINS` values move to the new origins (repo variable
  + env file; nothing in code).
- **Secrets**: production gets its OWN `SECRET_KEY` / `ENCRYPTION_KEY` and DB
  credentials (no sharing with staging/laptop), kept in the production host's
  env file or a secrets manager.
- **Deploy gate**: today every push to main auto-deploys staging. For
  production, add an environment with required reviewers on the deploy job
  rather than a new pipeline.
- **Data**: the section-5 volume reset stops being an option; schema changes
  go through Alembic (section 6, third row) from the first production deploy.

---

*Companion docs: `CICD_SETUP.md` (runner + GHCR bootstrap), `LOCAL_DEVELOPMENT_GUIDE.md`,
`MARIADB_10.1_COMPATIBILITY.md` (why 191-char index caps), `development_plan.md`.*
