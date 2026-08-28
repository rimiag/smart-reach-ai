# CI/CD Setup Guide — SmartReach AI

One push to `main` = lint → type-check/build → GHCR images → automatic staging deploy on your Ubuntu VM, with every deployment pinned to the exact commit that passed checks.

## Architecture

```
PR ──► backend-checks + frontend-checks          (GitHub-hosted runners)
           │ merge to main
           ▼
       build-backend / build-frontend            → ghcr.io/<owner>/smart-reach-ai-{backend,frontend}
           │                                       tagged sha-<short> (immutable) + latest
           ▼
       deploy-staging                            (self-hosted runner on the staging VM)
           • copies /opt/smart-reach-ai-staging/.staging.env into the fresh checkout
           • sources it, pulls sha-tagged images, `docker compose up -d`
           • polls /health + frontend until healthy
```

The runner lives **on** the staging VM and dials *out* to GitHub — no SSH port needs to be reachable from the internet.

## One-time setup

### A. GitHub repository configuration

| Item | Where | Value |
|------|-------|-------|
| Variable | Settings → Secrets and variables → Actions → Variables | `NEXT_PUBLIC_API_URL` = e.g. `http://<STAGING_VM_IP>:8000` |
| Environment | Settings → Environments → new `staging` | no reviewers = auto-deploy; add "Required reviewers" later to require approval |
| Secret (optional) | Actions secrets | `GHCR_PAT` — PAT with `read:packages` for pulling private images |

> **Important:** set `NEXT_PUBLIC_API_URL` **before** the first image build. Next.js bakes `NEXT_PUBLIC_*`
> into the client bundle at build time — changing it later requires a rebuild.

### B. Staging VM bootstrap (Ubuntu)

```bash
# 1. Docker Engine + compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # re-login afterwards

# 2. Deploy directory
sudo mkdir -p /opt/smart-reach-ai-staging
sudo chown -R $USER /opt/smart-reach-ai-staging

# 3. Deployment secrets - create once, never committed
cp .staging.env.example /opt/smart-reach-ai-staging/.staging.env   # then edit real values!
nano /opt/smart-reach-ai-staging/.staging.env                      # SECRET_KEY, MYSQL_ROOT_PASSWORD, OPENAI_API_KEY ...

# 4. GHCR login for pulling private images (skip if you set the GHCR_PAT secret)
echo "<PAT-read_packages>" | docker login ghcr.io -u <github-user> --password-stdin

# 5. GitHub self-hosted runner (repo Settings → Actions → Runners → New)
mkdir ~/actions-runner && cd ~/actions-runner
# ...download/link/configure per the on-screen instructions:
./config.sh --url https://github.com/rimiag/smart-reach-ai --token <TOKEN> --labels staging
sudo ./svc.sh install && sudo ./svc.sh start        # runs deploys unattended incl. after reboot
```

Runner user must be in the `docker` group (step 1) — the deploy job runs `docker compose` directly.

## How the pipeline works

1. **backend-checks** – Python 3.11, installs `requirements.txt`, enforces `black`/`isort`, smoke-imports `app.main`.
2. **frontend-checks** – Node 20, `npm ci`, `tsc --noEmit`, production `next build`.
3. **build-backend / build-frontend** (push to `main` only) – Buildx with GHA layer cache, pushes to GHCR as `sha-<short>` + `latest`; Trivy scans each image (report-only).
4. **deploy-staging** (needs both builds) – runs `docker compose up -d` straight from the fresh checkout of that commit (so compose always matches the code), sources `.staging.env`, recreates services pinned to `IMAGE_TAG=sha-<short>`, then health-gates `/health` and `/`.

## Operating

- **Redeploy same commit:** Actions → latest run → Re-run `Deploy to staging VM`.
- **Rollback:** open the previous green run → Re-run `Deploy to staging VM`. Or manually:
  from any clone of the repo: `git checkout <old-sha> && export IMAGE_TAG=sha-old1234 && docker compose up -d`
- **Flower monitoring:** `docker compose up -d` (included; UI on port 5555)
- **Logs:** `docker compose logs -f [service]`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Deploy job queued forever | Runner offline → on VM: `sudo ./svc.sh status` / restart it |
| Deploy can't pull images | GHCR auth: login during bootstrap or set `GHCR_PAT` secret |
| Frontend calls wrong API host | Repo variable `NEXT_PUBLIC_API_URL` missing/wrong at build time → fix variable, rebuild images |
| `_staging.env is missing` error | Create `/opt/smart-reach-ai-staging/.staging.env` from `.staging.env.example` |
| Health check times out | `docker compose logs backend` on the VM; DB may still be migrating on first boot (start_period=60s) |

## Recommended follow-ups

1. Add branch protection on `main` requiring the two check jobs.
2. First PRs will surface Dependabot bumps — review weekly batches.
3. Real `tests/` directory (pytest config already expects `testpaths=["tests"]`) so CI gates behavior, not just imports.
4. Revisit Alembic once schema changes begin (`init_db` creates tables but cannot evolve them).
5. flake8/mypy are configured but not yet gating in CI (existing debt); tighten later.
