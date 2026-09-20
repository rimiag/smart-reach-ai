# PROD_DEPLOYMENT.md — Production on your AWS EC2 (subdomains of your live domain)

This is the canonical guide for running smart-reach-ai in **production** on the EC2 instance
that already serves your website.

Related guides: STAGING_DEPLOYMENT.md (staging VM) · database/README.md (schema scripts) ·
CICD_SETUP.md (runner bootstrap details).

**App URL: `https://reachpulse.medidatalab.com` · API URL: `https://api.medidatalab.com`**
(Your website stays on its existing `medidatalab.com` nginx config — untouched.)

---

## 1. Architecture

```
browser ──HTTPS──▶ nginx (already on the EC2, ports 80/443, your website lives here)
                    ├── https://reachpulse.medidatalab.com  ──▶ 127.0.0.1:3000  (frontend)
                    └── https://api.medidatalab.com         ──▶ 127.0.0.1:8000  (backend)
                                                                  └─ internal docker network:
                                            db (MySQL 8) · redis · worker · scheduler · flower
```

- The **host nginx** (already serving your website) reverse-proxies the two subdomains to
  containers bound to **127.0.0.1 only**.
- **db, redis and flower have NO public ports at all** (docker-internal only). Unlike staging
  (a LAN-isolated VM), this host is internet-facing — nothing new gets exposed.
- Only **80/443 (+ SSH)** should be open in the AWS Security Group.
- Images come from GHCR (`prod-<sha7>` tags), built by `.github/workflows/ci-cd-prod.yml`.
  **Deploys are manual for both environments**: staging via Actions → "Build and Deploy" →
  Run workflow, prod via Actions → "Deploy to Production" → Run workflow. Pushing to main
  never deploys anything.

---

## 2. Prerequisites

| What | Where you get it |
|---|---|
| SSH + sudo on the EC2 | your existing access |
| DNS access for two A records | Route 53 or your registrar |
| `GHCR_PAT` repo secret | already exists (staging's deploy job uses it) |
| Provider keys (SERPAPI_KEY etc.) | same keys as staging, or dedicated prod keys |
| S3 bucket for offsite backups | `aws s3 mb s3://your-company-srcai-backups` (recommended) |

---

## 3. One-time EC2 setup

### 3.1 Security Group (AWS console)

Allow: **80, 443** (already open for your website) and your SSH port. **Do NOT open**
3000, 8000, 3306, 6379, 5555 — the containers bind to localhost or the docker network only.

Verify from your laptop afterwards:

```bash
# these must FAIL (timeout / refused):
nc -zv <EC2_PUBLIC_IP> 3306
nc -zv <EC2_PUBLIC_IP> 6379
nc -zv <EC2_PUBLIC_IP> 3000
nc -zv <EC2_PUBLIC_IP> 8000
# this must still SUCCEED:
curl -I https://medidatalab.com
```

### 3.2 Install Docker + Compose plugin

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER   # log out/in afterwards for the group to apply
docker compose version          # should print v2.x
```

### 3.3 Create the config directory + .prod.env

```bash
sudo mkdir -p /opt/smart-reach-ai-prod
sudo cp <local-checkout>/.prod.env.example /opt/smart-reach-ai-prod/.prod.env
sudo chmod 600 /opt/smart-reach-ai-prod/.prod.env
sudo nano /opt/smart-reach-ai-prod/.prod.env    # fill in real values, replace medidatalab.com
```

Key values: strong `DB_PASSWORD` / `MYSQL_ROOT_PASSWORD` / `SECRET_KEY` / `ENCRYPTION_KEY`
(generation commands are in the file's comments); URLs `https://api.medidatalab.com` /
`https://reachpulse.medidatalab.com`; `CORS_ORIGINS=https://reachpulse.medidatalab.com`;
`SERPAPI_KEY` etc.

### 3.4 DNS records

Create two **A records** pointing at the EC2 public IP (same IP as your website):

| Name | Type | Value |
|---|---|---|
| `reachpulse` | A | `<EC2_PUBLIC_IP>` |
| `api` | A | `<EC2_PUBLIC_IP>` |

Recommendation: convert the instance to an **Elastic IP** first if it doesn't have one —
auto-assigned public IPs change on stop/start, which would silently break DNS + certs.
Verify: `dig +short reachpulse.medidatalab.com` returns the EC2 IP from anywhere.

### 3.5 nginx vhosts for the two subdomains

Create `/etc/nginx/sites-available/reachpulse.conf`:

```nginx
# Frontend - reachpulse.medidatalab.com
server {
    listen 80;
    server_name reachpulse.medidatalab.com;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 90s;
    }
}

# API - api.medidatalab.com
server {
    listen 80;
    server_name api.medidatalab.com;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

Enable + reload:

```bash
sudo ln -s /etc/nginx/sites-available/reachpulse.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3.6 HTTPS via certbot (extends your existing Let's Encrypt setup)

```bash
sudo apt install -y certbot python3-certbot-nginx   # skip if certbot already installed
sudo certbot --nginx -d reachpulse.medidatalab.com -d api.medidatalab.com --redirect
```

certbot edits the two server blocks to serve HTTPS and adds HTTP→HTTPS redirects; its
systemd timer renews automatically. If it offers to expand an existing certificate instead,
that is fine too. Check with `sudo certbot certificates`.

### 3.7 GitHub Actions runner (label: prod)

Install it the same way as the staging VM's runner (CICD_SETUP.md has the full detail).
Summary:

```bash
# runner needs docker; the deploy job runs docker compose + docker login
sudo usermod -aG docker $USER
mkdir ~/actions-runner && cd ~/actions-runner
# download + configure from the EXACT commands GitHub shows you at:
#   repo Settings → Actions → Runners → New self-hosted runner → Linux x64
# In ./config.sh, when asked for labels, add:  prod
./config.sh --url https://github.com/rimiag/smart-reach-ai --token <token-from-github>
# then install as a service so it survives reboots:
sudo ./svc.sh install && sudo ./svc.sh start
```

The runner user must reach `/opt/smart-reach-ai-prod/.prod.env` (read) — install the runner
under your sudo login user, not a fresh system user, to keep this simple.

---

## 4. GitHub setup

1. GitHub → **Settings → Environments → New environment** → name: `production` (exact).
2. On the environment: **Add variable** (not secret):
   - Name: `NEXT_PUBLIC_API_URL` — Value: `https://api.medidatalab.com`
3. No required reviewers: the workflow is manual, so *you clicking "Run workflow" is the
   gate*. Add required reviewers later (environment settings) if teammates start pushing.

Why an environment variable: for jobs that declare `environment: production`,
**environment variables override repo variables** of the same name. Staging builds keep
reading the repo variable (staging VM URL); prod builds read the https API URL.

---

## 5. First deploy

1. Commit + push the prod files to `main` (pushing alone deploys nothing — both workflows
   are manual now).
2. Confirm DNS resolves: `dig +short reachpulse.medidatalab.com` / `api.medidatalab.com` both
   return the EC2 IP **before** running certbot (Let's Encrypt needs working DNS).
3. nginx vhosts enabled and reloaded (§3.5), certbot done (§3.6).
4. GitHub → Actions → **Deploy to Production** → Run workflow → leave `image_tag` EMPTY → Run.
5. Watch: build-backend → build-frontend → deploy-prod. Green requires backend `/health` and
   frontend :3000 to answer on the EC2. The first deploy is slower: MySQL 8 initializes an
   empty volume, then the backend entrypoint creates all tables.
6. Verify from your laptop:

```bash
curl -s https://api.medidatalab.com/health        # {"status":"ok",...}
curl -sI https://reachpulse.medidatalab.com       # HTTP/2 200 (or 307 to /login)
```

7. From outside, confirm nothing else answers:
   `nc -zv <EC2_PUBLIC_IP> 3306` must FAIL (same for 6379 / 3000 / 8000 / 5555).

---

## 6. Admin bootstrap

1. Register a normal account at `https://reachpulse.medidatalab.com/register` (e.g. your
   rizwancl@gmail.com account).
2. Promote it on the EC2 (works from any directory):

```bash
docker exec -it smart-reach-ai-prod-backend-1 python promote_admin.py <your-email>
```

3. Log out and back in — the **Admin** item appears in the sidebar.

---

## 7. Schema on prod

Same behavior as staging (STAGING_DEPLOYMENT.md §12-13):

- At every deploy the backend entrypoint **creates missing tables and auto-adds missing
  columns** (`ensure_schema`) — model changes self-apply on the next deploy.
- If the entrypoint ever fails, fall back to the manual scripts in `database/README.md`
  (`database/schema_full.sql`, `database/incremental/`). They are compatible with **MySQL 8
  and MariaDB**, so the same files serve prod and staging.
- Applying one manually on prod:

```bash
docker exec -i smart-reach-ai-prod-db-1 mysql -u root -p<PASSWORD> -D leadgen_db < database/schema_full.sql
```

(`-i`, not `-it`; `-D` is required — the guarded ALTERs use `DATABASE()`.)

---

## 8. Backups

### 8.1 The script

Create `/opt/smart-reach-ai-prod/backup.sh` (root-owned, `chmod 700`):

```bash
#!/usr/bin/env bash
# Nightly prod db backup: local gzip files (keep 7) + optional S3 upload.
set -euo pipefail
source /opt/smart-reach-ai-prod/.prod.env
BACKUP_DIR=/opt/backups
STAMP=$(date +%F_%H%M)
mkdir -p "$BACKUP_DIR"
docker exec smart-reach-ai-prod-db-1 sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers leadgen_db' \
  | gzip > "$BACKUP_DIR/leadgen_db_$STAMP.sql.gz"
ls -1t "$BACKUP_DIR"/leadgen_db_*.sql.gz | tail -n +8 | xargs -r rm --
# Offsite copy (only if BACKUP_S3_BUCKET is set in .prod.env and aws cli installed)
if [ -n "${BACKUP_S3_BUCKET:-}" ] && command -v aws >/dev/null 2>&1; then
  aws s3 cp "$BACKUP_DIR/leadgen_db_$STAMP.sql.gz" "s3://$BACKUP_S3_BUCKET/mysql/"
fi
```

Notes: `--single-transaction` dumps without locking tables (InnoDB); the `docker exec sh -c
'exec mysqldump -p"$MYSQL_ROOT_PASSWORD"'` form keeps the root password inside the container
instead of the host command line. On the S3 bucket, add a lifecycle rule to expire old
backups (e.g. 30 days) — that is your real retention.

### 8.2 Schedule it

```bash
sudo chmod 700 /opt/smart-reach-ai-prod/backup.sh
crontab -e       # as root: sudo crontab -e
# add:
30 2 * * * /opt/smart-reach-ai-prod/backup.sh >> /var/log/srcai-backup.log 2>&1
```

### 8.3 Backup drill (do it once, today)

Run the script by hand, check the file (`zcat /opt/backups/leadgen_db_*.sql.gz | head -30`
shows `CREATE TABLE` statements), then restore it into a throwaway database to prove the
dump is complete. An unrestored backup is a hope, not a backup. Restore steps:
database/README.md ("Full recovery").

---

## 9. Email deliverability

Before sending real outreach from prod, publish these DNS records for medidatalab.com (your
SMTP provider's docs give the exact values):

- **SPF** — TXT on `@`: `v=spf1 include:<provider-include> ~all` (Gmail:
  `include:_spf.google.com`). One SPF record per domain, merge includes into it.
- **DKIM** — the TXT/CNAME your SMTP provider generates (Gmail: Admin console → Apps →
  Google Workspace → Gmail → Authenticate email).
- **DMARC** — TXT on `_dmarc`: `v=DMARC1; p=none; rua=mailto:postmaster@medidatalab.com`
  (start with `p=none`, watch reports, tighten to quarantine/reject later).

Cold email from a fresh domain without these lands in spam — do this before the first real
campaign.

---

## 10. Monitoring

Add a free uptime monitor (UptimeRobot, Better Stack, ...) hitting
`https://api.medidatalab.com/health` every 5 minutes, alerting your email/phone. The backend
exposes `/health`; monitoring the frontend URL too costs nothing.

---

## 11. Troubleshooting

Where things live on the EC2:

| Thing | Location |
|---|---|
| prod env file | `/opt/smart-reach-ai-prod/.prod.env` |
| backup script + dumps | `/opt/smart-reach-ai-prod/backup.sh` → `/opt/backups/` |
| runner | `~/actions-runner` (service: `sudo ./svc.sh status`) |
| deployed code + compose files | `~/actions-runner/_work/smart-reach-ai/smart-reach-ai/` |

All compose commands run from the checkout directory and use
`-f docker-compose.prod.yml` (the checkout also contains the staging file — don't let
compose pick the wrong one):

```bash
cd ~/actions-runner/_work/smart-reach-ai/smart-reach-ai
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend   # or worker / db / ...
docker exec -it smart-reach-ai-prod-backend-1 python promote_admin.py <email>
```

| Symptom | Likely cause + fix |
|---|---|
| nginx 502 on smartreach./api. | a container is down: `docker compose -f docker-compose.prod.yml ps -a`, then `up -d`; `ss -tlnp \| grep -E "3000\|8000"` must show docker-proxy on 127.0.0.1 |
| backend unhealthy on FIRST deploy | MySQL 8 first boot initializes its data directory (1-2 min); db healthcheck allows 120s. Still failing → db logs |
| cert errors on the new subdomains | `sudo certbot certificates`; renewal is automatic (systemd timer); test with `sudo certbot renew --dry-run` |
| deploy can't pull from GHCR | repo secret `GHCR_PAT` expired → regenerate; or `docker login ghcr.io` once on the EC2 as fallback |
| runner offline | `cd ~/actions-runner && sudo ./svc.sh status` / `start`; check disk space |
| disk filling up | `docker system prune`; delete old `prod-<sha>` images in the GHCR package settings |
| MySQL 1045 Access denied | credential drift between .prod.env and the initialized volume — STAGING_DEPLOYMENT.md documents the reset; same steps with the prod container/volume names |
| emails not sending / spam | check `docker compose logs worker` for SMTP errors; re-check SPF/DKIM/DMARC (§9) |

---

## 12. Rollback

**Preferred:** Actions → Deploy to Production → Run workflow → set
`image_tag` = `prod-<older-sha7>` (find old tags in the GHCR package page or the previous
green runs' logs). This redeploys that image as-is — no rebuild.

**Manual (from the EC2):**

```bash
cd ~/actions-runner/_work/smart-reach-ai/smart-reach-ai
export IMAGE_TAG=prod-<older-sha7>
docker compose -f docker-compose.prod.yml up -d
```

Caveat: a rollback reverts CODE only. If the newer version auto-applied schema changes
(`ensure_schema`), the DB keeps those columns — that's harmless (extra columns don't break
the older code).

---

## 13. Appendix: import staging data (optional)

Prod starts with an **empty database** (recommended). If you want your staging data —
campaigns, leads, your user account — moved over instead:

**Important:** reuse the **same `ENCRYPTION_KEY`** value in prod's `.prod.env` as staging
uses, *before* the first prod deploy. Anything the app encrypted under staging's key is
unreadable under a different one.

1. Dump on the staging VM:

```bash
docker exec smart-reach-ai-staging-db-1 sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction leadgen_db' \
  > srcai-staging-dump.sql
```

2. Copy `srcai-staging-dump.sql` to the EC2 (scp/rsync), then load **into a fresh prod
   volume, before the first deploy** (or after `docker compose down` + volume delete if
   re-doing):

```bash
docker exec -i smart-reach-ai-prod-db-1 sh -c \
  'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" leadgen_db' < srcai-staging-dump.sql
```

3. `docker compose -f docker-compose.prod.yml up -d` (or re-run the workflow) and verify:
   login works, campaigns/leads are present.

MariaDB 10.1 → MySQL 8.0 dumps load cleanly here (the schema is engine-agnostic and both
sides were generated/verified from the same ORM metadata — see database/README.md).
