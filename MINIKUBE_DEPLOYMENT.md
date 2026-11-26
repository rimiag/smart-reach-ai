# Track 2 — Minikube Staging Deployment (step-by-step, handover-ready)

Deploy the SmartReach AI staging stack to Kubernetes (minikube, `none`
driver) on any Ubuntu VM, managed GitOps-style by Argo CD. Written so it
can be handed to another engineer and executed on a fresh VM unchanged.

**How the flow works:**

```
GitHub Actions ("Track 2" workflow) builds images ghcr.io/...:k8s-sha-<sha7>
   -> you bump the two newTag lines in infra/k8s/overlays/staging/kustomization.yaml
      (commit + push to the staging branch - the ONLY manual deploy step)
   -> Argo CD on the VM watches that folder and syncs the cluster
   -> app lives on NodePorts 30080 (frontend) / 30081 (API) / 30082 (flower)
```

**Rules (read once):**

1. Every numbered step has a **✅ Gate** — complete it before moving on.
2. Secrets are created out-of-band per cluster (`kubectl`), never in git.
3. Argo's `selfHeal` reverts manual `kubectl edit` changes to whatever git
   says — intended changes go through commits.
4. Do not run `docker compose` against any other project on this VM while
   deploying k8s — ports 30080–30083 must stay free.

---

## Part 0 — What you need before starting

| Item | Detail |
|---|---|
| VM | Ubuntu 22.04/24.04, **8 GB RAM / 4 vCPU min**, reachable by SSH |
| VM IP | The LAN IP k8s will serve on — used in `export VM_IP=` below |
| GitHub account | With push access to `rimiag/smart-reach-ai` |
| PAT #1 | Classic PAT with **`read:packages`** (image pulls) |
| PAT #2 (or same PAT) | **`repo`** scope / fine-grained **Contents: Read** (Argo reads the private repo) |
| `secrets.env` | A copy of `infra/k8s/secrets.env` — handed over privately, NEVER committed. If none exists: `cp infra/k8s/secrets.env.example infra/k8s/secrets.env` and fill real values (MYSQL_PASSWORD and DATABASE_URL must agree) |

> ⚠️ If this VM also runs another environment (e.g. the docker-compose
> staging on the original VM), verify 8 GB total RAM and free ports first:
> `free -h` (need ≥ 7 GiB total) and `ss -ltn | grep -E ':(30080|30081|30082|30083)'`
> (must print nothing).

---

## Part 1 — Prepare the VM (fresh Ubuntu, one-time)

SSH in, then:

```bash
# 1.1 Tools
sudo apt-get update && sudo apt-get install -y conntrack socat curl
curl -fsSL https://get.docker.com | sudo sh          # container runtime
sudo usermod -aG docker $USER                        # log out/in after this

# 1.2 kubectl
curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl && rm kubectl

# 1.3 minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64

# 1.4 Define the VM IP used by EVERY later step
export VM_IP=<this-vm-LAN-IP>        # e.g. 192.168.1.30 — set in EVERY new SSH session

# 1.5 Firewall (skip if ufw is inactive)
sudo ufw allow 30080/tcp && sudo ufw allow 30081/tcp && sudo ufw allow 30082/tcp && sudo ufw allow 30083/tcp
```

**✅ Gate 1:** `minikube version` + `kubectl version --client` print versions;
`echo $VM_IP` shows the IP; `curl -s http://checkip.amazonaws.com` works
(the VM needs outbound internet).

> The `none` driver runs the control plane directly on the VM, so NodePorts
> bind on `$VM_IP` itself — no port-forwarding needed, ever.

---

## Part 2 — Start the cluster

```bash
sudo minikube start --driver=none --memory=6g --cpus=3
sudo chown -R $USER $HOME/.kube                      # make kubeconfig user-readable
mkdir -p $HOME/.kube && sudo cp -i /root/.kube/config $HOME/.kube/config && sudo chown $USER $HOME/.kube/config
```

**✅ Gate 2:** `kubectl get nodes` → `minikube   Ready`.

---

## Part 3 — Cluster secrets (once per cluster, never in git)

```bash
# 3.1 App secret — copy secrets.env from your machine to the VM first, e.g.:
#     (on YOUR machine, repo root):
#     scp infra/k8s/secrets.env <user>@$VM_IP:/tmp/secrets.env
kubectl create namespace smartreach
kubectl -n smartreach create secret generic smartreach-env \
  --from-env-file=/tmp/secrets.env && rm /tmp/secrets.env

# 3.2 Image-pull secret for private GHCR images (name MUST be ghcr-pull)
kubectl -n smartreach create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<PAT with read:packages>
```

**✅ Gate 3:** `kubectl -n smartreach describe secret smartreach-env` lists
key names only (values never shown), and `kubectl -n smartreach get secret
ghcr-pull` exists. Confirm `MYSQL_PASSWORD` and `DATABASE_URL` in
secrets.env agreed before creating the secret.

---

## Part 4 — Point git at THIS VM, build the first images

The frontend's API URL is baked into its bundle at BUILD time, and the
configmap tells the backend which browser origin to allow. Both must use
`$VM_IP` — do this ONCE per VM **before** the first image build.

```bash
# 4.1 On your machine — repo, staging branch: set the repo variable so the
#     build bakes the right URL (GitHub → Settings → Variables → Actions,
#     or: gh variable set K8S_NEXT_PUBLIC_API_URL --body "http://$VM_IP:30081")

# 4.2 Edit infra/k8s/overlays/staging/patches/configmap.yaml — replace the
#     old VM IP in all three values with $VM_IP:
#       API_URL:       "http://<VM_IP>:30081"
#       FRONTEND_URL:  "http://<VM_IP>:30080"
#       CORS_ORIGINS:  "http://<VM_IP>:30080"
#     commit + push the staging branch
```

```bash
# 4.3 Run the first build:
#     GitHub → Actions → "Track 2 - Minikube Staging (build; Argo deploys)"
#     → Run workflow (branch dropdown is ignored — it always builds the
#       staging branch head). Wait for green.

# 4.4 Get the built tag and bump the overlay to it:
git ls-remote https://github.com/rimiag/smart-reach-ai staging | cut -c1-7
#     put k8s-sha-<that-sha> into BOTH newTag: lines in
#     infra/k8s/overlays/staging/kustomization.yaml, commit + push staging
```

**✅ Gate 4:** GHCR (repo → Packages) shows both
`smart-reach-ai-backend/frontend` with tag `k8s-sha-<sha7>`, and
`git log origin/staging -1` on your machine is the tag-bump commit.

---

## Part 5 — Argo CD (one-time)

```bash
# 5.1 Install + UI on NodePort 30083
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd get pods -w        # wait until ALL Running (~2 min), then Ctrl+C
kubectl -n argocd patch svc argocd-server \
  -p '{"spec":{"type":"NodePort","ports":[{"port":80,"nodePort":30083}]}}'

# 5.2 Initial admin password (user: admin — change it after first login)
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo

# 5.3 Give Argo read access to the private repo
kubectl -n argocd create secret generic smart-reach-ai-repo \
  --from-literal=type=git \
  --from-literal=url=https://github.com/rimiag/smart-reach-ai \
  --from-literal=username=<github-username> \
  --from-literal=password=<PAT with repo read>
kubectl -n argocd label secret smart-reach-ai-repo \
  argocd.argoproj.io/secret-type=repository

# 5.4 Register the Application
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
    path: infra/k8s/overlays/staging
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

Argo polls git every ~3 min; the UI **Refresh** button hurries it. The
first sync takes ~5 min (MySQL initializes → backend creates tables →
worker/scheduler/flower unblock).

**✅ Gate 5:** UI loads at `http://$VM_IP:30083`, all argocd pods Running,
and the `smartreach-staging` app appears (Synced or Progressing).

---

## Part 6 — Verification (deployment is confirmed ONLY here)

Run in order; a green Track 2 build alone proves nothing is deployed.

**V1 — Argo synced**

```bash
kubectl -n argocd get applications
# smartreach-staging   Synced   Healthy
```

**V2 — All workloads Running**

```bash
kubectl -n smartreach get pods
# mysql-0 1/1 (StatefulSet), backend, worker, scheduler, flower, frontend all 1/1 Running
```

**V3 — They run the NEW images (the commonly missed check)**

```bash
kubectl -n smartreach get deploy \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image'
# every app row must show :k8s-sha-<sha7> matching Part 4's tag
```

**V4 — Endpoints respond**

```bash
curl http://$VM_IP:30081/health        # {"status":"ok",...}
curl -sI http://$VM_IP:30080 | head -1 # HTTP/1.1 200
curl -sI http://$VM_IP:30082 | head -1 # flower
```

**V5 — Functional E2E**

```bash
# browser: http://$VM_IP:30080 -> register a user, log in (DB is empty on a new cluster)
kubectl -n smartreach logs deploy/backend | grep -E "tables|SCHEMA"   # "All required tables exist."
kubectl -n smartreach exec -it deploy/backend -- python promote_admin.py <registered-email>
# CORS proof:
curl -s -i -m 5 -X OPTIONS http://$VM_IP:30081/api/v1/auth/register \
  -H "Origin: http://$VM_IP:30080" -H "Access-Control-Request-Method: POST" | grep -i access-control
# expect: Access-Control-Allow-Origin: http://$VM_IP:30080
```

**✅ V1–V5 all pass = minikube staging is DEPLOYED AND VERIFIED.**

---

## Part 7 — Daily release / rollback / secret changes

```bash
# RELEASE
git push (code) -> staging branch
GitHub: Track 2 workflow -> Run -> green          # new k8s-sha-<sha7> in GHCR
edit BOTH newTag lines -> k8s-sha-<new-sha>       # overlays/staging/kustomization.yaml
commit + push -> staging branch
wait <= 3 min (or Argo UI Refresh)                # then re-run V1–V4

# ROLLBACK
git revert the tag-bump commit (or point both newTag lines at an older
k8s-sha-*) and push — Argo rolls the old images out. No VM access needed.

# SECRET CHANGE (secret is out-of-band; Argo never touches it)
kubectl -n smartreach delete secret smartreach-env
kubectl -n smartreach create secret generic smartreach-env --from-env-file=<updated-file>
kubectl -n smartreach rollout restart deploy
```

---

## Handover checklist (give this to the next person)

1. VM credentials + its LAN IP (their `$VM_IP`)
2. `secrets.env` — privately, never via chat/commit
3. GitHub username + PAT with `repo` + `read:packages` (and repo write
   access, or the engineer's own account with access)
4. This file — Parts 1–7 are the complete procedure, in order
5. Warning: if `$VM_IP` differs from the IP in
   `overlays/staging/patches/configmap.yaml` (committed git state) and the
   `K8S_NEXT_PUBLIC_API_URL` repo variable, Part 4 MUST be redone and the
   frontend rebuilt — otherwise the UI loads but API calls fail.
