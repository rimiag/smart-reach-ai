# GitOps on the staging VM — Argo CD (pull-based deployment)

The staging VM (192.168.1.30, minikube `none` driver) runs the K8s stack
**GitOps-style**: Git holds the desired state, Argo CD continuously pulls and
syncs it into the cluster. Nothing is pushed to the VM — no runner SSH, no
`kubectl apply` from CI.

```
push to staging branch
   -> Actions "Build K8s Images" -> GHCR ...:k8s-sha-<sha7>
   -> you bump the two newTag lines in overlays/staging/kustomization.yaml
      (commit + push - the only manual deploy step)
   -> Argo CD (watches infra/k8s/overlays/staging) syncs the cluster
   -> rollback = git revert; old tags stay in GHCR
```

**The GitOps contract:** with `selfHeal` on, any manual change on the cluster
(`kubectl edit`, `kubectl scale`, sed-ing a live configmap) is reverted to
what git says. ALL intended changes go through a commit to this repo.
Out-of-band exceptions (created once per cluster, never in git):
`smartreach-env` (app secrets) and `ghcr-pull` (GHCR image-pull secret) -
step 2 below.

## 1. Prerequisites (one-time)

- **VM RAM**: Argo CD adds ~0.8 GB on top of the stack. Bump the Hyper-V VM
  to 6-8 GB first (VM off -> Settings -> Memory). On the old 2.3 GB it will
  not fit.
- **Cluster**: minikube `none` driver running on the VM
  (`minikube start --driver=none`; `kubectl get nodes` -> Ready).
- **First images exist**: run Actions -> **Build K8s Images** once BEFORE
  registering the app (below), and put the resulting `k8s-sha-<sha7>` into
  `overlays/staging/kustomization.yaml` (commit + push). Registering an app
  that points at the placeholder tag `k8s-sha-0000000` just makes
  ImagePullBackOff noise.

## 2. One-time cluster secrets (never in git)

```bash
# on the laptop: scp infra/k8s/secrets.env root@192.168.1.30:<repo>/infra/k8s/
kubectl create namespace smartreach
kubectl -n smartreach create secret generic smartreach-env \
  --from-env-file=infra/k8s/secrets.env

# image-pull secret for the private GHCR images (5 app deployments
# reference it via the overlay patch). PAT needs read:packages.
kubectl -n smartreach create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<PAT with read:packages>
```

## 3. Install Argo CD (one-time)

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# UI on NodePort 30083 (none driver: bound on the VM IP directly)
kubectl -n argocd patch svc argocd-server \
  -p '{"spec":{"type":"NodePort","ports":[{"port":80,"nodePort":30083}]}}'

# initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

UI: `http://192.168.1.30:30083` (user `admin`, password above - change it
after first login or delete the initial secret). Wait for all argocd pods
Running first: `kubectl -n argocd get pods -w` (~2 min).

## 4. Give Argo read access to the repo (one-time)

The repo is private; Argo needs a PAT with **repo read** (classic PAT with
`repo` scope, or fine-grained Contents: Read). `read:packages` can live on
the same PAT so one token does both jobs.

```bash
kubectl -n argocd create secret generic smart-reach-ai-repo \
  --from-literal=type=git \
  --from-literal=url=https://github.com/rimiag/smart-reach-ai \
  --from-literal=username=<github-username> \
  --from-literal=password=<PAT with repo read>
kubectl -n argocd label secret smart-reach-ai-repo \
  argocd.argoproj.io/secret-type=repository
```

## 5. Register the Application (one-time)

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

Argo polls git every ~3 minutes; the UI **Refresh** button (or Hard Refresh)
forces it. First sync rolls out the whole stack (~3-5 min; MySQL
initializes first boot).

## 6. Everyday releases (the pull-based flow)

1. Push code to the `staging` branch.
2. Actions -> **Build K8s Images** -> Run workflow. Note the `k8s-sha-<sha7>`
   tag (workflow summary shows the resolved sha; the tag is that sha with
   the `k8s-sha-` prefix).
3. Edit the **two `newTag:` lines** in
   `infra/k8s/overlays/staging/kustomization.yaml` to that tag.
4. `git commit` + `git push origin staging`.
5. Argo CD notices (<=3 min) -> syncs -> the deployments roll. Watch the
   app in the UI (or press Refresh to hurry it).
6. Verify: `curl http://192.168.1.30:30081/health`, browser
   `http://192.168.1.30:30080`.

**Rollback**: `git revert` the tag-bump commit (or edit the two lines to an
older `k8s-sha-*` tag - they are never deleted from GHCR) and push. Argo
rolls the old images back out. No VM access needed.

## 7. Operations

```bash
kubectl -n argocd get apps                     # app status
kubectl -n argocd logs deploy/argocd-application-controller --tail=50
kubectl -n smartreach get deploy -o wide       # current images
kubectl -n argocd delete app smartreach-staging  # CAUTION: cascades - deletes
                                               # the managed workloads too
kubectl delete namespace argocd                # remove Argo itself
```

Sync defaults: automated + prune + selfHeal. To inspect what Argo WOULD
render before pushing: `kubectl kustomize infra/k8s/overlays/staging`.

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ImagePullBackOff` on `ghcr.io/...` | `ghcr-pull` secret missing/expired, or PAT lacks `read:packages`. Re-create it (step 2). Secret name must be exactly `ghcr-pull` |
| `ErrImagePull` 401/403 | GHCR PAT expired - re-create `ghcr-pull` |
| Argo: `ConfigurationError` / unknown repo | Repo credential wrong or PAT lacks repo read (step 4) |
| Sync fails with a validation error | Render locally to see the broken YAML: `kubectl kustomize infra/k8s/overlays/staging` |
| App stuck `OutOfSync` after a manual `kubectl` change | Working as designed - `selfHeal` reverts drift. Make the change in git instead |
| argocd pods Pending / OOMKilled | VM out of RAM - bump the Hyper-V memory, `minikube start --driver=none` again |
| Frontend loads but API calls fail | The bundle's baked URL no longer matches: rebuild the frontend with the right `K8S_NEXT_PUBLIC_API_URL` (Build K8s Images) AND check `patches/configmap.yaml` URLs agree |
| UI unreachable at :30083 | NodePort patch lost - re-run the svc patch (step 3); check `kubectl -n argocd get svc argocd-server` |

## 9. Later (out of scope today)

- **argocd-image-updater**: auto-commit new tags after each build (removes
  the manual step 3). Start manual; automate when it feels tedious.
- **Sealed Secrets / External Secrets**: move `smartreach-env` into git
  safely. Today it stays out-of-band (re-create per cluster).
- **Prod overlay**: `overlays/prod` (EKS) clones the staging overlay pattern;
  prod compose (EC2) is unaffected by everything in this file.
