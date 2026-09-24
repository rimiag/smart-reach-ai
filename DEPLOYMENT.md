# DEPLOYMENT.md — SmartReach AI (ReachPulse)

The single guide for running this app everywhere: **local**, **staging**, and
**production**, plus the database/schema-change playbook. Historical setup
guides were consolidated into this file; live ops questions start here.

- Staging app: `http://192.168.1.30:3000` · API `http://192.168.1.30:8000`
- Production app: `https://reachpulse.medidatalab.com` · API `https://api.medidatalab.com`

---

## 0. The three environments at a glance

| | Local (laptop) | Staging (Ubuntu VM) | Production (AWS EC2) |
|---|---|---|---|
| Runs natively? | Yes — uvicorn + next dev, no app containers | No — Docker Compose stack | No — Docker Compose stack |
| Compose file | none (only `db` + `redis` via `docker-compose.yml`) | `docker-compose.yml` (has `build:` sections too) | `docker-compose.prod.yml` (**pull-only**, no build sections) |
| Database | MariaDB/MySQL on localhost (or `docker-compose up -d db redis`) | `mariadb:10.1.48` container | `mysql:8.0` container |
| Env file | `backend/.env` + `frontend/.env.local` | `/opt/smart-reach-ai-staging/.staging.env` on the VM | `/opt/smart-reach-ai-prod/.prod.env` on the EC2 |
| How code deploys | You run it yourself | Actions → **Build and Deploy** → Run workflow (deploys the **staging branch**) | Build jobs via Actions → **Deploy to Production**, then **manual pull+up on the EC2** (§5.3) |
| Data policy | disposable | disposable test data | REAL — never reset casually |
| Exposed ports | 3000/8000 localhost | LAN-only VM (reachable from hypervisor host) | 80/443 only; containers bind `127.0.0.1`, db/redis have no ports |

---

## 1. How CI/CD works

Both workflows are **manual (`workflow_dispatch` only) and branch-pinned** —
pushing to any branch deploys nothing. You click the button; that is the gate.

```
Actions -> "Build and Deploy" (ci-cd.yml)          -> deploys the STAGING branch
   ├─ resolve: head of staging branch -> tag sha-<7>
   ├─ build backend  -> ghcr.io/rimiag/smart-reach-ai-backend:sha-<7> (+ latest)
   ├─ build frontend -> ghcr.io/rimiag/smart-reach-ai-frontend:sha-<7> (+ latest)
   └─ deploy: runs ON the VM (self-hosted runner, label `staging`)
         copies /opt/smart-reach-ai-staging/.staging.env into the fresh checkout,
         (optional) wipes the db volume if RESET_STAGING_DB=yes,
         sources env, pulls the sha-tagged images, docker compose up -d,
         polls backend /health + frontend :3000 until healthy

Actions -> "Deploy to Production" (ci-cd-prod.yml) -> builds from MAIN
   ├─ resolve: head of main -> tag prod-<7>
   ├─ build backend  -> ...backend:prod-<7> (+ prod-latest)
   ├─ build frontend -> ...frontend:prod-<7> (+ prod-latest)
   │    (frontend build requires the `production` GitHub Environment variable
   │     NEXT_PUBLIC_API_URL=https://api.medidatalab.com — it is baked into the bundle)
   └─ deploy-prod job exists for a `prod` self-hosted runner; if you deploy
      manually instead, follow §5.3 exactly (pull BEFORE up -d).
```

- Images are immutable per commit; rollback = redeploy an older tag (§4.7 / §5.8).
- The staging runner dials OUT to GitHub; the VM has no inbound internet.
- On staging deploy failure the workflow dumps `compose ps`, logs and VM
  resources into the run log before you need to SSH in.
- Changing repo variable `NEXT_PUBLIC_API_URL` or the VM's `.staging.env`
  requires a redeploy (Run workflow); only the frontend variable needs an
  image rebuild, env changes just need `up -d`.

## 2. One-time GitHub setup

Settings → Secrets and variables → Actions:

| Item | Type | Value |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Variable** (repo) | `http://192.168.1.30:8000` — baked into staging frontend builds at build time; set BEFORE first build (workflow falls back to exactly this) |
| `NEXT_PUBLIC_API_URL` | **Variable** on the `production` **Environment** (exact name) | `https://api.medidatalab.com` — environment variables override repo variables for jobs declaring `environment: production` |
| `GHCR_PAT` | Secret (optional) | PAT with `read:packages`, only if GHCR packages are private and the host hasn't `docker login ghcr.io` |

The **staging branch** is what the staging workflow deploys — create/refresh it
with `git push origin main:staging` when you want staging to test current main.

---

## 3. Local deployment (laptop, native — no app containers)

The laptop runs the app natively; Docker only provides MariaDB + Redis.

### 3.1 Prerequisites

Python 3.11+, Node.js 20+, Docker Desktop (for db/redis) or a local MariaDB/MySQL.

### 3.2 Database + Redis

Either start them from the repo (recommended — matches staging versions):

```bash
docker-compose up -d db redis     # from the repo root; mariadb:10.1 + redis on 6381
docker-compose ps
```

…or use a locally installed MariaDB/MySQL:

```sql
CREATE DATABASE leadgen_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'leadgen_user'@'localhost' IDENTIFIED BY 'leadgen_pass';
GRANT ALL PRIVILEGES ON leadgen_db.* TO 'leadgen_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3.3 Backend

```bash
cd backend
python -m venv .venv
.ven\Scripts\activate            # Windows (Git Bash: source .venv/Scripts/activate)
pip install -r requirements.txt

copy .env.example .env           # then edit; minimum:
#   DATABASE_URL=mariadb+aiomysql://<user>:<pass>@localhost:3306/leadgen_db
#   SECRET_KEY=<anything-long-and-random>
#   CORS_ORIGINS=http://localhost:3000
#   REDIS_URL / CELERY_BROKER_URL -> redis://localhost:6381/0 when using the compose redis
#   optional: SERPAPI_KEY, SMTP_*, IMAP_*, OPENAI/ANTHROPIC/GEMINI keys
```

Run it (three terminals, venv activated):

```bash
uvicorn app.main:app --reload --port 8000                 # API
celery -A app.tasks.celery_app worker --loglevel=info     # worker
celery -A app.tasks.celery_app beat --loglevel=info       # scheduler
```

First boot creates all tables from the ORM models (same entrypoint logic as
deployed environments — see §6.1). Verify: `curl http://localhost:8000/health`
and the Swagger UI at http://localhost:8000/docs.

### 3.4 Frontend

```bash
cd frontend
npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm run dev                       # http://localhost:3000
```

Type-check gate used everywhere (CI runs it in the Docker build):
`npx tsc --noEmit` from `frontend/`.

### 3.5 First run smoke test

1. Register at http://localhost:3000/register, log in.
2. Create a campaign (name + 5-10 keywords).
3. Run research (uses `SERPAPI_KEY`; without keys, staging-style dry runs still
   exercise the pipeline with stub providers in tests).
4. Review leads, generate emails, send (needs `SMTP_*`), check the Mailbox.

### 3.6 Bootstrap an admin locally

```bash
cd backend
python promote_admin.py <your-email>        # account must already exist
# other uses: --create --password <pw> (new admin), --revoke (demote)
```

---

## 4. Staging deployment (Ubuntu VM at 192.168.1.30)

### 4.1 One-time VM bootstrap

```bash
# 1. Docker Engine + compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER        # log out & back in

# 2. Secrets (never committed)
sudo mkdir -p /opt/smart-reach-ai-staging
sudo cp .staging.env.example /opt/smart-reach-ai-staging/.staging.env
sudo nano /opt/smart-reach-ai-staging/.staging.env   # real values, plain KEY=value lines

# 3. GHCR login - only if packages are private
echo "<PAT-with-read:packages>" | docker login ghcr.io -u rimiag --password-stdin

# 4. Self-hosted runner (Settings -> Actions -> Runners -> New self-hosted runner, Linux x64)
mkdir ~/actions-runner && cd ~/actions-runner
./config.sh --url https://github.com/rimiag/smart-reach-ai --token <RUNNER_TOKEN> --labels staging
sudo ./svc.sh install && sudo ./svc.sh start     # survives reboots
```

The VM is reachable only from the hypervisor host; the app lives at
`http://192.168.1.30:3000` (frontend), `:8000` (API), `:5555` (Flower).

### 4.2 The `.staging.env` file — what goes in it

Plain `KEY=value` lines (no quotes/spaces — the deploy job `source`s it).
Reuse your laptop `backend/.env` values for everything third-party; only the
group below must be staging-specific:

| Group | Keys |
|---|---|
| **Staging-specific (do NOT copy from laptop)** | `API_URL=http://192.168.1.30:8000` · `FRONTEND_URL=http://192.168.1.30:3000` · `CORS_ORIGINS=http://192.168.1.30:3000` · `DB_NAME=leadgen_db` · `DB_USER`/`DB_PASSWORD` (strong; they become the db account **only on a volume reset**, §4.6) · `MYSQL_ROOT_PASSWORD` |
| Copy verbatim from laptop `.env` | `SECRET_KEY`, `ENCRYPTION_KEY`, token-expiry settings, `SERPAPI_KEY`, AI keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, model names), `SMTP_*`, `IMAP_*`, `FOLLOW_UP_*`, optional tuning (`CELERY_*`, `RATE_LIMIT_*`, `CRAWLER_*`, limits, `DB_POOL_*`, `REDIS_CACHE_TTL`) |
| Omit — overridden by compose | `DATABASE_URL` (built as `mariadb+aiomysql://$DB_USER:$DB_PASSWORD@db:3306/$DB_NAME`), `REDIS_URL`/`CELERY_*URL` (forced to `redis://redis:6381/0`), `ENVIRONMENT`/`LOG_LEVEL`/`LOG_FORMAT` (forced `staging`/`INFO`/`json`), `NEXT_PUBLIC_API_URL` (GitHub **variable**, not env-file), `IMAGE_TAG` (pipeline) |

Empty provider keys stay empty — that simply switches that feature off (AI
assistant answers return a clear "no AI provider configured" error).

### 4.3 Deploying (normal flow)

1. Push the code you want to test: `git push origin main:staging`.
2. GitHub → Actions → **Build and Deploy** → Run workflow.
3. A green run = images pushed AND stack healthy on the VM.
4. Redeploy the same commit without a push: the run → Re-run all jobs.

### 4.4 Post-deploy checklist

```bash
# from the hypervisor host:
curl http://192.168.1.30:8000/health     # 200 {"status":"ok"}
curl -I http://192.168.1.30:3000         # HTTP 200

# on the VM (find the checkout with `docker compose ls`):
docker compose ps                        # every service Up (healthy)
docker logs --tail 50 smart-reach-ai-staging-backend-1
                                         # expect "All required tables exist."
                                         # SCHEMA: lines = ensure_columns ALTERs (§6.1)
```

Browser: register/log in, create a campaign, run a search, (if SMTP) send a
test email, check Flower at `http://192.168.1.30:5555`.

### 4.5 Everyday ops on the VM

There is no permanent copy of the app files in `/opt` — only the secrets.
The compose file lives in the runner checkout, refreshed on every deploy:

```
/opt/smart-reach-ai-staging/.staging.env                 <- secrets (permanent)
~/actions-runner/_work/smart-reach-ai/smart-reach-ai/    <- compose + code (per-deploy)
```

`docker compose ls` prints the checkout path — `cd` there (or add
`-p smart-reach-ai-staging`) for all compose commands:

```bash
docker compose ps                                  # status + health
docker compose logs --tail 100 backend             # any service: frontend backend
docker compose logs -f backend                     #   worker scheduler flower db redis
docker compose restart backend                     # one container in place
docker compose up -d                               # apply env/image changes (recreates
                                                   #   containers whose config changed)
docker compose stop / start / down / up -d         # down keeps volumes/data
docker stats --no-stream                           # CPU/RAM
```

Gotchas:

- **`restart` does NOT re-read `.staging.env`** — env is injected at container
  creation. After editing the env file run `docker compose up -d`.
- Never edit files in the checkout (next deploy replaces it). Permanent
  change = commit; permanent secret = the `/opt` env file.
- Data lives in named volumes (`*_mysql_data`, `*_redis_data`,
  `_celerybeat-data`); only `down -v` or RESET_STAGING_DB deletes data.
- VM reboot: docker + `restart: unless-stopped` bring everything back alone.
- After `stop`, give the backend ~60s (`start_period`) before judging health.

### 4.6 One-time staging DB reset (data-destructive)

The MariaDB image applies `MYSQL_USER`/`MYSQL_PASSWORD`/`MYSQL_DATABASE` only
when its data volume is EMPTY — later env edits never reach the volume. When
credentials/schema drift (1045 Access denied) and staging data is disposable:

```bash
# 1. Make sure /opt/smart-reach-ai-staging/.staging.env is correct first —
#    the reset bakes THOSE values into the fresh volume.
# 2. Arm the reset (repo variable):
gh variable set RESET_STAGING_DB -R rimiag/smart-reach-ai --body yes
# 3. Actions -> Build and Deploy -> Run workflow. The deploy stops/removes db,
#    deletes the mysql_data volume, and up -d re-initializes from current env;
#    the backend then creates all tables.
# 4. Checklist (§4.4) green, then DISARM:
gh variable set RESET_STAGING_DB -R rimiag/smart-reach-ai --body no
```

After a reset, users must register again. Never leave the variable `yes`.

### 4.7 Staging rollback

Images are immutable per commit: Actions → the older GREEN run → Re-run all
jobs (rebuilds are cache-hits; the deploy re-pins IMAGE_TAG to that sha).
Manual on the VM: `export IMAGE_TAG=sha-<old7> && docker compose up -d`.
Rollback moves code, not the database — plan schema changes (§6) first.

### 4.8 Admin bootstrap on staging

```bash
cd ~/actions-runner/_work/smart-reach-ai/smart-reach-ai
docker compose exec backend python promote_admin.py <your-email>
# then reload the browser - the Admin sidebar item appears
```

---

## 5. Production deployment (EC2 — reachpulse / api .medidatalab.com)

Architecture: the EC2's existing host nginx (which already serves your
website) reverse-proxies the two subdomains to containers bound to
127.0.0.1; db/redis/flower have no public ports at all.

```
browser --HTTPS--> nginx (host, 80/443)
   https://reachpulse.medidatalab.com -> 127.0.0.1:3000 (frontend)
   https://api.medidatalab.com        -> 127.0.0.1:8000 (backend) -> internal docker net:
                                             db (mysql:8.0) . redis . worker . scheduler . flower
```

### 5.1 One-time EC2 bootstrap

1. **Security Group**: only 80/443 (+ SSH). Verify from outside that
   `nc -zv <EC2_IP> 3306|6381|3000|8000|5555` all FAIL.
2. **Docker**: `sudo apt install -y docker.io docker-compose-v2` +
   `sudo usermod -aG docker $USER`.
3. **Env file**: `sudo mkdir -p /opt/smart-reach-ai-prod && sudo cp
   .prod.env.example /opt/smart-reach-ai-prod/.prod.env && sudo chmod 600 …`,
   fill real values (strong `DB_PASSWORD`/`MYSQL_ROOT_PASSWORD`/`SECRET_KEY`/
   `ENCRYPTION_KEY` — generation commands in the file's comments; URLs
   `https://api.medidatalab.com` / `https://reachpulse.medidatalab.com`;
   `CORS_ORIGINS=https://reachpulse.medidatalab.com`; provider keys).
4. **DNS**: A records `reachpulse` + `api` → EC2 IP. Use an Elastic IP
   (auto-assigned public IPs change on stop/start and silently break DNS +
   certs). Verify with `dig +short` BEFORE certbot.
5. **nginx vhosts**: `/etc/nginx/sites-available/reachpulse.conf` with two
   server blocks (proxy to 127.0.0.1:3000 / :8000, `proxy_set_header Host
   $host`, X-Forwarded-*, websocket upgrade on the frontend block,
   `client_max_body_size 20m`), enable + `sudo nginx -t && sudo systemctl
   reload nginx`. (The complete ready-to-paste vhost file is preserved in git
   history under its old name PROD_DEPLOYMENT.md §3.5.)
6. **HTTPS**: `sudo certbot --nginx -d reachpulse.medidatalab.com -d
   api.medidatalab.com --redirect` (extends the existing Let's Encrypt
   setup; renewal is automatic — check `sudo certbot certificates`).
7. **GitHub Environment**: Settings → Environments → new environment named
   exactly `production`, add VARIABLE `NEXT_PUBLIC_API_URL=https://api.medidatalab.com`.
8. **(Optional) `prod` self-hosted runner** on the EC2 (same steps as §4.1,
   label `prod`; runner user must read /opt/smart-reach-ai-prod/.prod.env).
   Not installed today — §5.3 is the manual equivalent and works fine.

### 5.2 First deploy

1. Commit + push to `main` (pushing alone deploys nothing).
2. GitHub → Actions → **Deploy to Production** → Run workflow → leave
   `image_tag` EMPTY → Run. This builds both images and pushes them to GHCR.
3. Watch build-backend → build-frontend go green (first MySQL 8 boot
   initializes its volume in 1-2 min; the backend entrypoint then creates all
   tables — allow several minutes before judging health).
4. Verify:

```bash
curl -s https://api.medidatalab.com/health        # {"status":"ok",...}
curl -sI https://reachpulse.medidatalab.com       # HTTP/2 200 (or 307 -> /login)
```

5. Admin bootstrap: register at `/register`, then
   `docker exec -it smart-reach-ai-prod-backend-1 python promote_admin.py <email>`
   and log in again.

### 5.3 Ongoing deploys — manual flow (READ THE GOTCHA)

`docker-compose.prod.yml` is **pull-only**: the EC2 containers run GHCR images
and never read the git checkout. `docker compose up -d` **never pulls newer
images** — it reuses whatever is already on the host, so skipping the pull
silently keeps the OLD version running (this exact mistake shipped a stale
prod during the mailbox release, 2026-09-23).

The reliable sequence on the EC2:

```bash
cd ~/actions-runner/_work/smart-reach-ai/smart-reach-ai   # or any checkout of main
git pull origin main

# 1. Get the new images built: Actions -> Deploy to Production -> Run workflow
#    (image_tag EMPTY). Wait for build-backend + build-frontend green.

# 2. Sanity-check the env file is not pinning an old image:
grep IMAGE_TAG /opt/smart-reach-ai-prod/.prod.env
#    must say prod-latest (or the NEW prod-<sha7>); a pinned old sha freezes the version.

# 3. Pull, THEN recreate:
docker compose --env-file /opt/smart-reach-ai-prod/.prod.env -f docker-compose.prod.yml pull
docker compose --env-file /opt/smart-reach-ai-prod/.prod.env -f docker-compose.prod.yml up -d --remove-orphans
```

Post-deploy signal that the new image really started:

```bash
docker compose -f docker-compose.prod.yml ps
docker logs smart-reach-ai-prod-backend-1 2>&1 | grep SCHEMA   # ALTERs (§6.1), if any
```

If a `prod` self-hosted runner is ever installed on the EC2, the workflow's
deploy-prod job does pull + up + health checks for you; until then step 1 +
step 3 above IS the deploy.

### 5.4 Backups

`/opt/smart-reach-ai-prod/backup.sh` (root-owned, chmod 700) — nightly dump,
keep 7 local, optional S3 offsite (`BACKUP_S3_BUCKET` in `.prod.env` + aws cli):

```bash
#!/usr/bin/env bash
set -euo pipefail
source /opt/smart-reach-ai-prod/.prod.env
BACKUP_DIR=/opt/backups
STAMP=$(date +%F_%H%M)
mkdir -p "$BACKUP_DIR"
docker exec smart-reach-ai-prod-db-1 sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers leadgen_db' \
  | gzip > "$BACKUP_DIR/leadgen_db_$STAMP.sql.gz"
ls -1t "$BACKUP_DIR"/leadgen_db_*.sql.gz | tail -n +8 | xargs -r rm --
if [ -n "${BACKUP_S3_BUCKET:-}" ] && command -v aws >/dev/null 2>&1; then
  aws s3 cp "$BACKUP_DIR/leadgen_db_$STAMP.sql.gz" "s3://$BACKUP_S3_BUCKET/mysql/"
fi
```

Cron it as root: `30 2 * * * /opt/smart-reach-ai-prod/backup.sh >>
/var/log/srcai-backup.log 2>&1`. **Drill the restore once** — restore into a
throwaway database (steps: [database/README.md](database/README.md) "Full
recovery"). An unrestored backup is a hope, not a backup. The
`docker exec sh -c 'exec mysqldump -p"$PW"'` form keeps the password off the
host command line; on the prod container root is safe because the volume was
initialized from the current `.prod.env`.

### 5.5 Email deliverability (before real outreach)

Publish for medidatalab.com (values from your SMTP provider): **SPF** (one TXT
on `@`, merge includes), **DKIM** (provider-generated TXT/CNAME), **DMARC**
(TXT on `_dmarc`, start `p=none`, tighten later). Cold email from a fresh
domain without these lands in spam.

### 5.6 Monitoring

Uptime monitor (UptimeRobot/Better Stack) on
`https://api.medidatalab.com/health` every 5 min; watching the frontend URL
too costs nothing.

### 5.7 Rollback

**Preferred:** Actions → Deploy to Production → Run workflow with
`image_tag=prod-<older-sha7>` (find tags on the GHCR package page or previous
green runs) — then run §5.3 step 3 so the host actually pulls that tag.
**Manual:** on the EC2 `export IMAGE_TAG=prod-<older-sha7>` before the
`up -d`. Caveat: rollback reverts CODE only; columns ensure_schema added stay
(harmless — extra columns don't break older code), but plan any data-affecting
change before rolling back.

### 5.8 Moving staging data to prod (clone, not merge)

The dump REPLACES prod tables (`DROP`+`CREATE` inside); afterwards you log in
with your STAGING password, and accounts registered only on prod are gone.

1. **Align keys**: copy staging's `SECRET_KEY`/`ENCRYPTION_KEY` into
   `.prod.env`, `up -d` on the EC2 to re-inject (JWTs re-sign = re-login).
2. **Snapshot prod** (your undo point) with the §5.4 dump command to
   `/opt/backups/pre-import_<stamp>.sql.gz`.
3. **Dump staging** as the APP user, not root (root's password drifts on
   staging volumes — the healthcheck proves the app user's creds):

```bash
# on the staging VM:
docker exec smart-reach-ai-staging-db-1 sh -c \
  'exec mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" --single-transaction leadgen_db' \
  > srcai-staging-dump.sql
# copy staging VM -> admin machine -> EC2 (scp hop via your laptop)
```

4. **Import on the EC2** (API down for the duration; frontend stays up):

```bash
cd ~/actions-runner/_work/smart-reach-ai/smart-reach-ai
docker compose -f docker-compose.prod.yml stop backend worker scheduler
docker exec -i smart-reach-ai-prod-db-1 sh -c \
  'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" leadgen_db' < ~/srcai-staging-dump.sql
docker exec smart-reach-ai-prod-redis-1 redis-cli -p 6381 FLUSHALL   # stale celery state
docker compose -f docker-compose.prod.yml up -d
```

5. **Verify**: count campaigns/leads/research_results/users vs staging; admin
   flag missing → `promote_admin.py <email>`. Staging keeps running unchanged;
   the datasets diverge from this moment. MariaDB 10.1 → MySQL 8.0 dumps load
   cleanly (schema is engine-agnostic — see §6.4).

---

## 6. Database schema & migrations guide

### 6.1 How schema changes actually apply (all deployed environments)

The ORM models in `backend/app/models/` are the single source of truth. Every
backend-family container start (backend, worker, scheduler) runs
`backend/docker-entrypoint.sh`, which:

1. waits for the db to accept connections,
2. computes the required tables from `Base.metadata` (never a hardcoded list),
3. `create_all` for missing **tables** (never alters existing ones),
4. `ensure_schema.ensure_columns()` - compares ORM columns vs the live DB and
   runs `ALTER TABLE ... ADD COLUMN` for anything missing (compiled by
   SQLAlchemy for the running engine: MariaDB, MySQL, PostgreSQL alike),
5. re-verifies and exits 1 (container fails loudly) if anything is still missing.

Watch it work: `docker logs <backend-container> | grep SCHEMA` - shows each
auto-ALTER, and `SCHEMA: could not add missing column <stmt>` if a manual
fallback is needed. **Known limitations**: no type changes or column drops
auto-apply, NOT NULL columns need `server_default` on the model (else the
ALTER fails on populated tables), and indexes on new columns are not
auto-created (add those by hand).

**Adding a nullable column = commit the model change and deploy. That is it.**
Anything beyond that, use the decision rule below.

### 6.2 Alembic (backend/alembic/versions/ 001-009)

Alembic migrations exist as a repo convention/history but are **NOT wired into
any deploy** - never rely on them running automatically. Deployed DBs converge
via create_all + ensure_columns (§6.1). Local devs may use
`alembic upgrade head` on a fresh DB or ignore it entirely.

### 6.3 Changing a model - decision rule

| Situation | What to do |
|---|---|
| Adding a nullable column (any env) | Just change the model; ensure_columns applies it on next deploy. NOT NULL? add `server_default=` to the column. |
| Staging, data disposable | §4.6 one-time volume reset. Simplest, always correct. |
| Keep the data, few columns | Manual ALTER on the host, e.g. `docker exec -it smart-reach-ai-staging-db-1 mysql -u root -p leadgen_db -e "ALTER TABLE leads ADD COLUMN follow_up_count INT NOT NULL DEFAULT 0;"` (or the exact statement the SCHEMA log printed). |
| Real data, frequent changes | Wire Alembic into the entrypoint (replace create_all with `alembic upgrade head`) - and `alembic stamp head` FIRST on DBs built by create_all, or Alembic tries to re-create existing tables. |

`create_all` never alters existing tables - that is why the rows above exist.
Test your change locally first (§3): drop the column, restart the backend,
watch it heal - same code path as deployed environments.

### 6.4 Manual schema scripts (fallback when the entrypoint cannot run)

[database/README.md](database/README.md) is the run guide. Contents:

- `database/schema_full.sql` - full fresh-DB schema, **auto-generated from the
  ORM** by `cd backend && python generate_schema_sql.py` (run after every model
  change and commit together). Idempotent (`CREATE TABLE IF NOT EXISTS`,
  FK-checks-off wrapper, inline KEY clauses). MySQL-8-flavored DDL, valid on
  MariaDB 10.1+ too - the same file serves staging and prod.
- `database/incremental/*.sql` - guarded, re-runnable ALTERs for existing DBs
  (information_schema checks + PREPARE/EXECUTE).

```bash
# staging (note: -i not -it; -D is REQUIRED - the guards call DATABASE()):
docker exec -i smart-reach-ai-staging-db-1 sh -c \
  'exec mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -D leadgen_db' < database/schema_full.sql
# prod:
docker exec -i smart-reach-ai-prod-db-1 sh -c \
  'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -D leadgen_db' < database/schema_full.sql
```

### 6.5 Named traps

1. **MYSQL_USER/PASSWORD/DATABASE only apply on an EMPTY volume** - editing
   them in the env file later does nothing until a reset (§4.6) or an in-db
   `ALTER USER`. This caused the 2026-09-11 staging outage.
2. `backend/db/init.sql` hardcodes the database name (`ALTER DATABASE
   leadgen_db ...`) - if you ever change `DB_NAME`, change init.sql too.
3. Dumping a staging volume as **root** can 1045 (same drift) - dump as the
   app user via the container's own env (§5.8 step 3).

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Staging deploy: backend logs `Access denied (1045)` for the app user | Volume creds drifted from `.staging.env` -> §4.6 reset, or keep data: `ALTER USER '<user>'@'%' IDENTIFIED BY '<env-pw>'; FLUSH PRIVILEGES;` |
| Staging deploy fails at db healthcheck (used to pass) | The healthcheck does a real login now - it is telling the truth; same fix as above |
| Backend unhealthy, "tables missing" in logs | Entrypoint failed; read the dump-diagnostics step / `docker compose logs backend` - it names the table. Check `DATABASE_URL` interpolation |
| Deploy job queued forever | Runner offline: on the VM `sudo ~/actions-runner/svc.sh status` (stop/start to restart); on EC2 `cd ~/actions-runner` then `sudo ./svc.sh status` |
| Deploy cannot pull from GHCR | Private package + no login: `docker login ghcr.io -u rimiag` or set the `GHCR_PAT` secret; on prod also check the PAT has not expired |
| `.staging.env is missing` / `.prod.env is missing` | Create it from the corresponding `.example` file |
| Frontend calls the wrong API host | `NEXT_PUBLIC_API_URL` variable missing/wrong at BUILD time (baked into the bundle) -> fix variable, re-run the workflow |
| **Prod not picking up new code** | §5.3: you skipped `docker compose pull`, or `IMAGE_TAG` in `.prod.env` pins an old sha. Pull first, then `up -d` |
| Prod deploy: first-boot backend unhealthy | MySQL 8 initializes its data dir 1-2 min (healthcheck allows 120 s). Still failing -> db logs |
| Frontend CI build: `Missing: @emnapi/... from lock file` | Lockfile regenerated on Windows (image is alpine/musl). In `frontend/`: `npx -y npm@11.19.0 install --package-lock-only --os=linux --cpu=x64 --libc=musl`, commit, re-run. Any local `npm install` re-clobbers it |
| Assistant/AI returns 400 "no AI provider configured" | No AI key in that environment's env file - add to BOTH laptop `.env` and the server env, redeploy |
| Staging data vanished | `RESET_STAGING_DB` variable was left `yes` -> set `no` (§4.6 step 5) |
| Subdomain shows the OTHER website | No nginx block claims that `server_name` (or certbot put the names into the other site's block): inspect with `sudo nginx -T` (grep server_name), fix the vhosts, reload, re-run certbot |
| nginx 502 | A container down: `docker compose -f docker-compose.prod.yml ps -a`, then `up -d`; check with `ss -tlnp` that docker-proxy listens on 127.0.0.1 for 3000/8000 |
| Cert errors | `sudo certbot certificates`; renewals are automatic; test with `sudo certbot renew --dry-run` |
| Disk filling up | `docker system prune`; delete old `prod-<sha>` images in the GHCR package settings |
| Emails not sending / spam-foldered | `docker compose logs worker` for SMTP errors; check SPF/DKIM/DMARC (§5.5) |
| Entrypoint edits crash the backend | No double quotes anywhere inside the entrypoint's `python -c` block; verify by RUNNING it locally (`bash docker-entrypoint.sh true` with DATABASE_URL set), not just `bash -n` |

---

## 8. Related docs

| Doc | Contents |
|---|---|
| [README.md](README.md) | What the product is, quick start, stack |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Full build history: every iteration, feature, and lesson |
| [database/README.md](database/README.md) | Manual schema scripts: usage, verification, full recovery |
| [MARIADB_10.1_COMPATIBILITY.md](MARIADB_10.1_COMPATIBILITY.md) | Why indexed strings are capped at 191 chars (utf8mb4 on MariaDB 10.1) |
