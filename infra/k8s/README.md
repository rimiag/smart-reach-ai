# Kubernetes (minikube) — SmartReach AI

Deploy the whole stack to a local minikube cluster with plain Kubernetes
manifests (no Helm, no Kustomize). This is the first step of the K8s path:
**minikube now → staging/prod on managed K8s (EKS) later** — the manifests are
written so that move changes configuration, not structure.

## TL;DR — every command in order

```bash
# 0. cluster up (first time: --memory=4096 --cpus=2; if an old profile is
#    stuck with "apiserver process never appeared": minikube delete first)
minikube start --memory=4096 --cpus=2
kubectl get nodes                       # expect: minikube  Ready

# 1. build both images into minikube's docker daemon
#    (backend first build = several minutes; both run from INSIDE the
#    subdirectory - `minikube image build` on Windows fails with
#    "lstat .../backend: no such file" when the context is a subdir)
cd "/c/Users/Rizwan/Desktop/Office Work/Devops-work/ai agent/smart-reach-ai/backend"
minikube image build -f Dockerfile -t smartreach-ai/backend:local .

#    Frontend needs --build-arg (the API URL is baked at build time), which
#    `minikube image build` does NOT support -> use minikube's docker daemon:
cd ../frontend
eval $(minikube -p minikube docker-env)
docker build --build-arg NEXT_PUBLIC_API_URL=http://$(minikube ip):30081 \
  -f Dockerfile -t smartreach-ai/frontend:local .
cd ..

# 2. secrets (fill real values; same password in MYSQL_PASSWORD and DATABASE_URL)
kubectl create namespace smartreach     # needed before the secret
cp infra/k8s/secrets.env.example infra/k8s/secrets.env
nano infra/k8s/secrets.env              # or: notepad infra/k8s/secrets.env
kubectl -n smartreach create secret generic smartreach-env \
  --from-env-file=infra/k8s/secrets.env

# 3. bake your minikube IP into the configmap (one-time, do not commit)
sed -i "s/__MINIKUBE_IP__/$(minikube ip)/g" infra/k8s/02-configmap.yml

# 4. apply everything and watch it come up (~3-5 min first boot)
kubectl apply -f infra/k8s/
kubectl -n smartreach get pods -w       # Ctrl+C when all Running 1/1

# 5. verify
curl http://$(minikube ip):30081/health # {"status":"ok",...}
# browser: http://<minikube-ip>:30080  (register, log in)
# flower:  http://<minikube-ip>:30082

# 6. admin (after registering in the browser)
kubectl -n smartreach exec -it deploy/backend -- python promote_admin.py <your-email>
```

Detailed explanation of each step + ops + troubleshooting below.

```
browser (your laptop)
   ├── http://<minikube-ip>:30080  -> frontend Service (NodePort) -> frontend pod
   ├── http://<minikube-ip>:30081  -> backend  Service (NodePort) -> backend pod
   └── http://<minikube-ip>:30082  -> flower  Service (NodePort) -> flower pod

namespace "smartreach":
   backend (FastAPI) ── mysql (StatefulSet, PVC)      cluster-internal:
   worker  (Celery)  ── redis  (Deployment)           mysql:3306, redis:6379
   scheduler (beat)  ── [same image as backend]
   flower  (Celery monitor)
```

| File | What it creates |
|---|---|
| `01-namespace.yml` | the `smartreach` namespace |
| `02-configmap.yml` | non-secret config (has a `__MINIKUBE_IP__` placeholder — step 4) |
| `03-mysql.yml` | MySQL 8 StatefulSet + Service + 5Gi PVC |
| `04-redis.yml` | Redis 7 Deployment + Service (6379 in-cluster) |
| `05-backend.yml` | FastAPI backend Deployment + Service (NodePort **30081**) |
| `06-worker.yml` | Celery worker Deployment (waits for backend via initContainer) |
| `07-scheduler.yml` | Celery beat Deployment |
| `08-flower.yml` | Flower Deployment + Service (NodePort **30082**) |
| `09-frontend.yml` | Next.js frontend Deployment + Service (NodePort **30080**) |
| `secrets.env.example` | template for the `smartreach-env` Secret (step 3) |

Key facts before you start:

- **Images are built inside minikube** (`minikube image build`) with the tag
  `smartreach-ai/backend:local` / `smartreach-ai/frontend:local`. Nothing is
  pulled from a registry; the manifests use `imagePullPolicy: IfNotPresent`.
- **The frontend bakes its API URL at build time**
  (`http://<minikube-ip>:30081`). If the cluster IP changes (recreated
  cluster), rebuild the frontend image (step 2) and redeploy it.
- **The database password is fixed on first boot** of the MySQL volume —
  changing `secrets.env` later does not change it (delete the PVC to reset;
  minikube data is disposable).
- Schema management is automatic and identical to every other environment:
  the backend entrypoint waits for MySQL, creates missing tables and adds
  missing columns (`ensure_schema`) on boot. See DEPLOYMENT.md §6.

## Prerequisites

- minikube + kubectl on the PATH (`minikube version`, `kubectl version --client`).
- ~4 GB RAM to give the cluster — the whole stack (MySQL 8 is the heaviest
  pod) does not fit comfortably in the 2 GB default.
- Docker Desktop does NOT need to be running — `minikube image build` builds
  inside minikube's own daemon.

## Step 1 — Start the cluster

```bash
minikube start --memory=4096 --cpus=2
kubectl config current-context     # must print: minikube
kubectl get nodes                  # must show minikube Ready
```

## Step 2 — Build the images (into minikube's docker daemon)

Run from INSIDE each subdirectory. On Windows, `minikube image build` fails
with `lstat .../backend: no such file or directory` when the build context is
a subdirectory of the current dir — building with `.` from inside the folder
avoids it. The FIRST backend build takes several minutes (pip installs);
later builds are fast (layer cache).

```bash
# Backend API image
cd backend
minikube image build -f Dockerfile -t smartreach-ai/backend:local .
cd ..

# Frontend image — NEXT_PUBLIC_API_URL is baked into the JS bundle at build
# time and must point at the NodePort URL the browser will use. It needs
# --build-arg, which `minikube image build` does NOT support, so point your
# docker CLI at minikube's daemon instead:
cd frontend
eval $(minikube -p minikube docker-env)      # Git Bash / WSL; PowerShell:
                                             #   minikube -p minikube docker-env | Invoke-Expression
docker build --build-arg NEXT_PUBLIC_API_URL=http://$(minikube ip):30081 \
  -f Dockerfile -t smartreach-ai/frontend:local .
cd ..
```

(Your local Docker Desktop does not need to be running — these builds happen
inside the minikube node. `frontend/.dockerignore` keeps node_modules out of
the build context.)

```bash
minikube image ls | grep smartreach-ai       # confirm both are there
```

## Step 3 — Create the Secret (never committed)

The namespace must exist first (the Secret is created inside it):

```bash
kubectl create namespace smartreach

cd infra/k8s
cp secrets.env.example secrets.env
# edit secrets.env: pick a strong MYSQL_PASSWORD, put the SAME password in
# DATABASE_URL, set SECRET_KEY, add your provider keys (SERPAPI_KEY,
# SMTP_*, ...). Keys left empty simply switch that feature off.
cd ../..

kubectl -n smartreach create secret generic smartreach-env \
  --from-env-file=infra/k8s/secrets.env

kubectl -n smartreach get secret smartreach-env   # confirm
```

`secrets.env` is gitignored. If you later change it, re-create the secret and
restart the pods that use it:

```bash
kubectl -n smartreach delete secret smartreach-env
kubectl -n smartreach create secret generic smartreach-env \
  --from-env-file=infra/k8s/secrets.env
kubectl -n smartreach rollout restart deploy
```

## Step 4 — Point the ConfigMap at your minikube IP (one-time)

`02-configmap.yml` contains the placeholder `__MINIKUBE_IP__`. Replace it
with your cluster IP:

```bash
sed -i "s/__MINIKUBE_IP__/$(minikube ip)/g" infra/k8s/02-configmap.yml
grep MINIKUBE infra/k8s/02-configmap.yml    # should print nothing now
```

The IP is machine-specific — **do not commit the substituted file**
(`git checkout infra/k8s/02-configmap.yml` restores the placeholder).

## Step 5 — Apply everything

```bash
kubectl apply -f infra/k8s/
```

Watch it come up (MySQL first boot initializes its data directory, then the
backend waits for it, creates tables, starts — allow ~3-5 minutes the first
time):

```bash
kubectl -n smartreach get pods -w
# mysql-0        1/1 Running
# backend-...    1/1 Running
# worker-...     1/1 Running   (initContainer "wait-for-backend" runs first)
# scheduler-...  1/1 Running
# flower-...     1/1 Running
# frontend-...   1/1 Running
```

## Step 6 — Verify

```bash
IP=$(minikube ip)
curl http://$IP:30081/health      # {"status":"ok",...}   (API)
curl -I http://$IP:30080          # HTTP/1.1 200          (frontend)
```

Then in the browser:

1. Open `http://<minikube-ip>:30080`, register a user, log in.
2. Create a campaign, run research (needs `SERPAPI_KEY` in the secret).
3. Flower (Celery monitor): `http://<minikube-ip>:30082`.
4. Promote your account to admin:

```bash
kubectl -n smartreach exec -it deploy/backend -- python promote_admin.py <your-email>
```

5. Schema proof: `kubectl -n smartreach logs deploy/backend | grep -E "tables|SCHEMA"`
   should show "All required tables exist." (or the create + ensure_columns
   output on the very first boot).

## Everyday operations

```bash
# look
kubectl -n smartreach get pods,svc
kubectl -n smartreach logs -f deploy/backend        # or worker / scheduler / ...
kubectl -n smartreach describe pod -l component=backend

# restart one component (picks up configmap/secret changes too)
kubectl -n smartreach rollout restart deploy/backend

# scale (worker is the one that benefits)
kubectl -n smartreach scale deploy/worker --replicas=2

# shell into a pod
kubectl -n smartreach exec -it deploy/backend -- bash

# after changing CODE: rebuild the image, then restart the deployments
# that use it (frontend additionally needs the build-arg, see step 2):
minikube image build -f backend/Dockerfile -t smartreach-ai/backend:local backend/
kubectl -n smartreach rollout restart deploy/backend deploy/worker deploy/scheduler deploy/flower
```

Rollback: rebuild/retag an older commit's image as `:local` and
`rollout restart` — same idea as every other environment (images are
immutable per build; you redeploy an older one).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `minikube image build`: `lstat /var/lib/minikube/build/.../backend: no such file` | Windows subdirectory-context bug — run the build from INSIDE the folder with `.` as context (step 2) |
| `minikube image build`: `unknown flag: --build-arg` | Not supported — build the frontend via `eval $(minikube docker-env)` + `docker build --build-arg` (step 2) |
| Pod `ImagePullBackOff` for `smartreach-ai/*` | Image not built inside minikube (or tag typo). Run step 2; check `minikube image ls` |
| mysql `Pending` forever | Cluster out of memory/disk for the PVC — `kubectl -n smartreach describe pod mysql-0`, give minikube more RAM (`minikube start --memory=4096`) |
| mysql CrashLoop on a REUSED cluster | Old volume has the old password baked in (first-boot rule). Data is disposable here: `kubectl -n smartreach delete statefulset mysql; kubectl -n smartreach delete pvc data-mysql-0; kubectl apply -f infra/k8s/03-mysql.yml` |
| backend CrashLoop, logs show DB connect errors | Secret's `DATABASE_URL` does not match `MYSQL_USER`/`MYSQL_PASSWORD`/`MYSQL_DATABASE`, or password has unencoded special chars. Fix secrets.env, re-create secret (step 3), reset the PVC if the volume already initialized |
| backend CrashLoop with a Python traceback | Read `kubectl -n smartreach logs deploy/backend --previous`; the entrypoint exits 1 loudly if tables could not be created |
| worker stuck in `Init:0/1` | The init container cannot reach `http://backend:8000/health` — check the backend pod is Running/ready first (`kubectl -n smartreach get pods -l component=backend`) |
| Frontend loads but API calls fail (CORS/console errors) | The bundle's baked URL no longer matches: `minikube ip` changed (cluster recreated) or `02-configmap.yml` still has `__MINIKUBE_IP__`. Fix the configmap AND rebuild the frontend image (step 2), restart both |
| Everything Pending after `minikube start` | Node not Ready yet — `kubectl get nodes`, wait; if stuck: `minikube delete && minikube start --memory=4096 --cpus=2` |
| Emails/research do nothing | Those provider keys are empty in the secret — features switch off silently, same behavior as staging (AI assistant returns a clear "no provider" error) |

## Teardown

```bash
kubectl delete namespace smartreach        # removes everything incl. the MySQL PVC
# or nuke the whole cluster:
minikube delete
```

## Path to EKS (what changes later)

This folder is the rehearsal. Moving to managed K8s later is mostly
configuration, in this order:

1. **Images**: push to GHCR (the CI already builds `prod-<sha7>` tags) and
   switch `image:` values + add `imagePullSecrets` for the private packages.
2. **Database**: replace the MySQL StatefulSet + PVC with **Amazon RDS** —
   the app only knows `DATABASE_URL`, so it is a secret change, not a code
   change. (Keep the StatefulSet for dev clusters.)
3. **Ingress**: NodePort Services become ClusterIP; an Ingress (ALB on EKS,
   nginx on minikube — the addon is already enabled) fronts frontend + API
   with real hostnames/TLS.
4. **Secrets**: move `smartreach-env` to AWS Secrets Manager / External
   Secrets; the key names stay identical.
5. **Environment overlays**: at that point copy this folder per environment
   (`overlays/staging`, `overlays/prod`) or introduce Kustomize — the object
   shapes stay the same.
6. **Redis**: ElastiCache, same swap pattern as the DB.
