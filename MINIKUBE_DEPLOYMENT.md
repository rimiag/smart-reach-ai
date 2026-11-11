# Track 2 — Minikube Staging: Deployment & Confirmation Runbook

Operational runbook for the GitOps minikube staging environment on the VM
(192.168.1.30). Every stage has a **confirmation gate** — do not start the
next stage until the current one passes.

This doc covers the VM staging cluster end to end. The one-time bring-up
details live in `infra/k8s/GITOPS.md`; the local (laptop) minikube flow is
`infra/k8s/README.md`; the schema/init behavior is DEPLOYMENT.md §6.

## The rules (read once)

1. **Track 1 (VM docker-compose staging) is untouchable.** Nothing in this
   doc runs `docker compose` on the VM. The k8s stack and the compose stack
   share the VM only as neighbors: k8s NodePorts (30080–30083) do not
   collide with the compose ports (3000/8000/…), and the k8s MySQL lives in
   its own PVC — it has nothing to do with the compose MariaDB volume.
2. **All deploys are pull-based.** GitHub Actions only builds images
   (`k8s-sha-*`). Argo CD deploys by watching `infra/k8s/overlays/staging`
   on the `staging` branch. The ONLY manual deploy action in this track is
   bumping the two `newTag:` lines + pushing.
3. **The "Run workflow" branch dropdown is cosmetic.** Track 2 always builds
   the head of the `staging` branch, whatever the dialog says (same for
   Track 1 / EC2 prod — each workflow pins its own branch).
4. **Secrets never go into git or k8s YAML.** `smartreach-env` and
   `ghcr-pull` are created once per cluster, out-of-band.
5. **selfHeal contract:** manual `kubectl edit/scale/patch` on managed
   resources gets reverted to git. Intended changes go through commits.
   (Out-of-band secrets are the only exception.)

## Resource budget on the shared VM

Bump the Hyper-V VM to **8 GB RAM / 4 vCPU** first (VM off → Settings →
Memory). Rough budget: compose staging ~1.5–2 GB, GitHub runner ~0.5 GB,
Argo CD ~0.8 GB, app stack + MySQL 8 ~2.5–3 GB, control plane ~0.5 GB.
Check anytime with `free -h` — `available` under ~1.5 GiB means you are
close to the OOM zone (an OOM here can kill BOTH tracks).

---

# Stage 0 — What state am I in? (diagnosis)

SSH to the VM (`rizwan@192.168.1.30`) and run:

```bash
free -h                                          # total >= 7 GiB? else bump RAM first
minikube status                                  # host/kubelet/apiserver all: Running
kubectl get nodes                                # minikube / Ready  (no NotReady)
kubectl -n argocd get pods                       # Argo installed? (see table)
kubectl -n argocd get applications               # app registered?
kubectl -n smartreach get all,secret,pvc         # anything deployed?
docker ps                                        # compose staging still Up? (sanity)
```

Interpret the result:

| Observation | Meaning | Where to resume |
|---|---|---|
| `No resources found in argocd namespace` (what we saw 2026-11-11) | argocd namespace exists, Argo pods unknown | Stage 1 → then Stage 3+ |
| `No resources found in smartreach namespace` | nothing deployed yet (normal pre-bring-up) | continue bring-up |
| argocd pods Running + app missing | Argo up, app not registered | Stage 4 (§ Register the Application) |
| app exists, `smartreach` empty, app not Synced | repo credential or image problem | Stage 4 § repo-credential, troubleshooting |
| `minikube status` fails / apiserver missing | stale profile | `minikube delete` then Stage 1 |

**State on 2026-11-11:** namespaces exist; no Argo pods confirmed; no app;
nothing deployed → resume at **Stage 1**, skipping only what passes its gate.

---

# Stage 1 — Cluster up

```bash
minikube start --driver=none --memory=6g --cpus=3   # no-op if already running
kubectl get nodes
```

**✅ Gate 1:** `kubectl get nodes` shows `minikube  Ready`. Compose staging
still Up in `docker ps`. NodePorts are free:

```bash
ss -ltn | grep -E ':(30080|30081|30082|30083)'   # must print nothing (yet)
```

Note: the `none` driver runs the control plane directly on the VM, so
NodePorts bind on the VM IP (192.168.1.30) directly — no port-forward step
is needed in this track. If `minikube start` was ever run with sudo and
your user's kubectl can't reach the cluster, merge the kubeconfig:
`sudo cat /root/.kube/config >> ~/.kube/config` (or run kubectl with sudo
consistently — pick one and stay with it).

---

# Stage 2 — One-time cluster secrets (out-of-band, never in git)

### 2a. App secret

`infra/k8s/secrets.env` is gitignored — copy it from the laptop:

```bash
# ON THE LAPTOP (Git Bash, repo root):
scp "infra/k8s/secrets.env" rizwan@192.168.1.30:/tmp/secrets.env

# ON THE VM:
kubectl -n smartreach create secret generic smartreach-env \
  --from-env-file=/tmp/secrets.env && rm /tmp/secrets.env
```

**✅ Gate 2a:** `kubectl -n smartreach describe secret smartreach-env`
prints the KEY NAMES with `(binary)` values and nothing leaked. Check the
critical pair: `MYSQL_PASSWORD` and `DATABASE_URL` must agree (same user,
same password) — a mismatch is the classic 1045 Access-denied crash-loop.

### 2b. GHCR image-pull secret

The 5 app deployments pull private `ghcr.io/rimiag/*` images via the
`ghcr-pull` secret (wired by `overlays/staging/patches/imagepull.yaml`).
Needs a classic PAT with **read:packages**:

```bash
kubectl -n smartreach create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<PAT with read:packages>
```

**✅ Gate 2b:** `kubectl -n smartreach get secret ghcr-pull` exists, and the
same PAT works:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer <same-PAT>" \
  https://ghcr.io/token\?scope\=repository:rimiag/smart-reach-ai-backend:pull
# expect 200
```

---

# Stage 3 — First images + tag bump (the deploy trigger)

Argo deploys whatever the overlay says — so the overlay must point at real
images BEFORE the Application is registered, or the first sync just makes
ImagePullBackOff noise.

1. **GitHub → Actions → "Track 2 - Minikube Staging (build; Argo deploys)"
   → Run workflow** (branch: anything — it is ignored). Wait for green.
2. Note the resolved sha from the run summary — or compute it:

```bash
git ls-remote https://github.com/rimiag/smart-reach-ai staging | cut -c1-7
```

3. On the laptop, edit **both** `newTag:` lines in
   `infra/k8s/overlays/staging/kustomization.yaml` to
   `k8s-sha-<that-sha>`, then commit + push the **staging** branch.

**✅ Gate 3:** both images exist in GHCR
(github.com/rimiag/smart-reach-ai → Packages) with tag `k8s-sha-<sha7>`,
and `git log origin/staging -1` shows the tag-bump commit.

---

# Stage 4 — Argo CD install + repo access

### 4a. Install Argo CD

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd get pods -w          # wait until ALL Running (~2 min)

kubectl -n argocd patch svc argocd-server \
  -p '{"spec":{"type":"NodePort","ports":[{"port":80,"nodePort":30083}]}}'

kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo   # login: admin
```

If the VM runs ufw: `sudo ufw allow 30080/tcp 30081/tcp 30082/tcp 30083/tcp`.

**✅ Gate 4a:** UI loads at `http://192.168.1.30:30083` (admin + password
above; change it after first login). All argocd pods Running.

### 4b. Repo read credential

Argo must read the PRIVATE repo — PAT with **repo** scope (classic) or
fine-grained **Contents: Read**. One PAT can carry both `repo` and
`read:packages` and serve steps 2b and 4b.

```bash
kubectl -n argocd create secret generic smart-reach-ai-repo \
  --from-literal=type=git \
  --from-literal=url=https://github.com/rimiag/smart-reach-ai \
  --from-literal=username=<github-username> \
  --from-literal=password=<PAT with repo read>
kubectl -n argocd label secret smart-reach-ai-repo \
  argocd.argoproj.io/secret-type=repository
```

**✅ Gate 4b:** verified only indirectly at Stage 5 — if the app shows
`ConfigurationError: unknown repository`, this credential is wrong.

### 4c. Register the Application

```bash
cat << 'YAML' | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: smartreach-staging
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/rimiag/smart-reach-ai
    targetRevision: staging          # tracks the staging branch head
    path: infra/k8s/overlays/staging # the kustomize overlay
  destination:
    server: https://kubernetes.default.svc
    namespace: smartreach
  syncPolicy:
    automated:
      prune: true     # resources removed from git get removed from cluster
      selfHeal: true  # manual cluster edits get reverted to git
    retry:
      limit: 5
      backoff: { duration: 15s, factor: 2, maxDuration: 5m }
YAML
```

Argo polls git every ~3 min; UI **Refresh** hurries it. First sync rolls out
the whole stack — MySQL initializes its data directory on first boot, then
backend creates tables, then worker/scheduler/flower unblock — allow
~5 min.

---

# Stage 5 — Verification ladder (the confirmation gates)

Run IN ORDER. Each step proves one link of the chain; a green Track 2 build
alone proves NOTHING is deployed.

**V1 — Argo synced the app**

```bash
kubectl -n argocd get applications
# NAME                SYNC STATUS   HEALTH STATUS    AGE
# smartreach-staging  Synced        Healthy          ...
```

| means | Synced + Healthy = git state == cluster state. |
|---|---|
| OutOfSync | mid-reconcile (wait/Refresh) or manual drift |
| Progressing | rollout in progress |
| ConfigurationError | step 4b credential broken |

**V2 — Workloads actually exist and run**

```bash
kubectl -n smartreach get pods
# mysql-0                          1/1 Running      (StatefulSet)
# backend-<id>                     1/1 Running
# worker-<id>                      1/1 Running      (Init:0/1 until backend is up)
# scheduler-<id>                   1/1 Running
# flower-<id>                      1/1 Running
# frontend-<id>                    1/1 Running
```

`kubectl -n smartreach get deploy` listing SIX deployments (backend, worker,
scheduler, flower, frontend + none missing) with READY `1/1` is the gate.
`mysql-0` is a StatefulSet, not a deployment.

**V3 — They run the NEW images (the step people forget to check)**

```bash
kubectl -n smartreach get deploy -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image'
```

Every app row must show `ghcr.io/rimiag/smart-reach-ai-*:k8s-sha-<sha7>`
matching Stage 3's tag. **Argo can be perfectly Synced and still running
yesterday's images if you forgot the tag bump — V3 is the check that
catches it.**

**V4 — Health endpoints**

```bash
curl http://192.168.1.30:30081/health        # {"status":"ok",...}
curl -sI http://192.168.1.30:30080 | head -1 # HTTP/1.1 200
curl -sI http://192.168.1.30:30082 | head -1 # flower UI
```

**V5 — Functional E2E (browser)**

1. `http://192.168.1.30:30080` → register a fresh user (this k8s MySQL is
   EMPTY — it shares nothing with the compose staging DB), log in.
2. Backend log shows schema bootstrap ran:
   `kubectl -n smartreach logs deploy/backend | grep -E "tables|SCHEMA"`
   → "All required tables exist."
3. Promote admin:
   `kubectl -n smartreach exec -it deploy/backend -- python promote_admin.py <email>`
4. CORS proof (frontend bundle talks to :30081 directly):
   `curl -s -i -m 5 -X OPTIONS http://192.168.1.30:30081/api/v1/auth/register -H "Origin: http://192.168.1.30:30080" -H "Access-Control-Request-Method: POST" | grep -i access-control`
   → `Access-Control-Allow-Origin: http://192.168.1.30:30080`
5. Sanity: compose staging STILL works (`docker ps` Up, browser
   `http://192.168.1.30` staging frontend unchanged).

**✅ Stage 5 complete = minikube staging is VERIFIED.** Only then proceed
to EKS.

---

# Stage 6 — Everyday releases (and rollback)

```bash
# RELEASE
git push (code) -> staging branch
GitHub: Track 2 workflow -> Run -> green   (images k8s-sha-<new7> in GHCR)
edit BOTH newTag lines -> k8s-sha-<new7>   (overlays/staging/kustomization.yaml)
git commit + push -> staging branch
wait <=3 min (or Argo UI Refresh)          -> re-run V1..V4

# ROLLBACK
git revert the tag-bump commit (or edit the two lines to an older k8s-sha-*)
push -> Argo rolls the old images out. No VM access needed. Old tags are
never deleted from GHCR.
```

Changing `secrets.env` later: re-create the secret + restart workloads
(Argo won't touch it — it's out-of-band):

```bash
kubectl -n smartreach delete secret smartreach-env
kubectl -n smartreach create secret generic smartreach-env --from-env-file=<path>
kubectl -n smartreach rollout restart deploy
# (re-run the port-forwards-free curl checks after)
```

---

# Troubleshooting (VM cluster)

| Symptom | Cause / fix |
|---|---|
| App `OutOfSync` forever after a manual `kubectl` change | Working as designed — `selfHeal` reverts drift to git. Make changes via commits |
| App `ConfigurationError` / unknown repo | Step 4b secret wrong or PAT lacks repo read — re-create it |
| Pods `ImagePullBackOff` on ghcr.io images | `ghcr-pull` missing/expired or PAT lacks read:packages — re-create (2b). Name must be exactly `ghcr-pull` |
| argocd pods Pending / OOMKilled | VM RAM exhausted — `free -h`; bump Hyper-V memory, then `minikube start --driver=none` again |
| mysql-0 Pending forever | PVC can't bind (disk/memory) — `kubectl -n smartreach describe pod mysql-0` |
| mysql CrashLoop on a reused cluster | Old volume has an old password (first-boot rule). k8s data is disposable: `kubectl -n smartreach delete statefulset mysql pvc data-mysql-0` → next sync re-creates it |
| backend CrashLoop, logs show 1045 Access denied | `DATABASE_URL` ≠ MYSQL_* in the secret — fix secrets.env, re-create secret, restart |
| backend CrashLoop with Python traceback | `kubectl -n smartreach logs deploy/backend --previous` — entrypoint exits loudly if tables missing |
| worker stuck `Init:0/1` | init container waiting for backend `/health` — fix backend first |
| Frontend loads, API calls fail (console CORS errors) | Baked bundle URL vs configmap mismatch — rebuild frontend via Track 2 with right `K8S_NEXT_PUBLIC_API_URL` (default `http://192.168.1.30:30081`) AND check `patches/configmap.yaml` URLs agree; then re-bump tag |
| AI assistant / email features dead | Provider keys empty in `secrets.env` — features switch off silently (same as all envs) |
| Compose staging got slow/OOM | k8s stack is squeezing it — `free -h`; lighten Argo replicas or consider separating the clusters |
| UI :30083 unreachable | NodePort patch lost — re-run the svc patch (4a) |

---

# What NOT to do on the VM

- Never run `docker compose` targeting the staging compose project from
  k8s work — the two tracks share the VM, not the stack.
- Never `kubectl delete namespace smartreach` unless you intend to wipe the
  k8s environment (it takes the PVC + MySQL data with it).
- Never commit `secrets.env`, PATs, or the real configmap values.
- Never rely on the workflow's branch dropdown to pick a target — it is
  cosmetic on every workflow in this repo.
