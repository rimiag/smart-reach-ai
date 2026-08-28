# CI/CD Setup Guide — SmartReach AI

One push to `main` = backend image build + frontend image build + automatic
deploy to the staging VM (**192.168.1.30**). Nothing else — no PR checks, no
dependency bots, no vulnerability scanners.

## How it works

```
push to main
   ├─ build backend image  → ghcr.io/rimiag/smart-reach-ai-backend:sha-<short> (+ latest)
   ├─ build frontend image → ghcr.io/rimiag/smart-reach-ai-frontend:sha-<short> (+ latest)
   └─ deploy               → runs ON the staging VM (self-hosted runner)
         • copies /opt/smart-reach-ai-staging/.staging.env into the fresh checkout
         • sources it, pulls the sha-tagged images, `docker compose up -d`
         • polls backend /health + frontend until healthy
```

The runner lives on the VM and dials OUT to GitHub — the VM keeps no inbound
internet access. GitHub's cloud runners cannot reach `192.168.1.30` (private
LAN IP), which is exactly why the runner must run on the VM itself.

Rollback: Actions → older green run → **Re-run all jobs** (images are pinned
per commit, so nothing newer leaks in).

## One-time setup

### GitHub (Settings → Secrets and variables → Actions)

| Item | Where | Value |
|------|-------|-------|
| Variable | Variables tab | `NEXT_PUBLIC_API_URL` = `http://192.168.1.30:8000` — baked into the frontend bundle at build time, so set it BEFORE the first build (the workflow falls back to exactly this URL if unset) |
| Secret (optional) | Secrets tab | `GHCR_PAT` — PAT with `read:packages`, only needed if the GHCR packages are private and the VM hasn't run `docker login ghcr.io` |

### Staging VM (192.168.1.30, Ubuntu)

```bash
# 1. Docker Engine + compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER        # then log out & back in

# 2. Deployment secrets (never committed)
sudo mkdir -p /opt/smart-reach-ai-staging
sudo cp .staging.env.example /opt/smart-reach-ai-staging/.staging.env
sudo nano /opt/smart-reach-ai-staging/.staging.env   # real SECRET_KEY, DB passwords, OPENAI_API_KEY ...

# 3. GHCR login - only if packages are private and no GHCR_PAT secret is set
echo "<PAT-with-read:packages>" | docker login ghcr.io -u rimiag --password-stdin

# 4. Self-hosted runner (repo Settings → Actions → Runners → New self-hosted runner)
mkdir ~/actions-runner && cd ~/actions-runner
# ...download/link per the on-screen instructions, then:
./config.sh --url https://github.com/rimiag/smart-reach-ai --token <RUNNER_TOKEN> --labels staging
sudo ./svc.sh install && sudo ./svc.sh start     # survives reboots
```

The runner's user must be in the `docker` group (step 1) — the deploy job runs
`docker compose` directly against the local daemon.

## Daily use

| Task | How |
|------|-----|
| Deploy | Push to `main`. Watch it under the **Build and Deploy** workflow. |
| Redeploy same commit | Actions → the run → **Re-run all jobs** |
| Rollback | Actions → older green run → **Re-run all jobs** |
| Logs on the VM | `docker ps` / `docker logs -f <container>` |
| Manage the stack on the VM | `cd` into the runner's checkout dir (under `~/actions-runner/_work/...`) and use `docker compose` normally |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Deploy job queued forever | Runner offline → on the VM: `sudo ./svc.sh status`, restart it |
| Deploy can't pull images | GHCR auth: run `docker login ghcr.io` on the VM or set the `GHCR_PAT` secret |
| `.staging.env is missing` error | Create `/opt/smart-reach-ai-staging/.staging.env` from `.staging.env.example` |
| Frontend talks to the wrong API host | `NEXT_PUBLIC_API_URL` repo variable was missing/wrong when images were built → fix variable, re-run the workflow |
| Health check times out | `docker logs backend` on the VM — first boot also creates DB tables (start period 60 s) |

## Notes

- Dependabot has been **removed** (it was opening the flood of upgrade PRs).
  Its existing PRs will be auto-closed once this lands on `main`; anything left
  over: `gh pr list --state open` then close, or close them in the web UI.
- The "Security" tab alerts come from GitHub's dependency scanning — harmless
  to leave on, or disable under Settings → Code security.
- When real tests exist, a `pytest` job can be added ahead of the builds.
- Revisit Alembic before real data accumulates (`init_db` creates tables but
  cannot evolve an existing schema).
