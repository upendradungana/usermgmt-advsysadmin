# User Management Service on Kubernetes (minikube)

Practical assignment: *Deploying a Scalable User Management Application on Kubernetes*
College of Science and Technology, Royal University of Bhutan

| | |
|---|---|
| Student ID (`<sid>`) | `02230158` |
| Namespace | `usermgmt-02230158` |
| Host name | `usermgmt-02230158.local` |
| Cluster | minikube (Docker driver), Ingress controller: **ingress-nginx** (minikube `ingress` add-on) |
| Application image | `usermgmt-api:1.0` (built locally, loaded into the cluster, no registry) |

**How to read this file**

1. [Installation and setup](#1-installation-and-setup): what the project is, file structure, tools, cluster, add-ons, VPA.
2. [Apply and run](#2-apply-and-run-milestone-by-milestone): how to deploy each milestone, with what happens and what output to expect.
3. [Evidence checks](#3-evidence-checks-milestone-by-milestone): commands that prove each milestone works.
4. [Other commands and troubleshooting](#4-other-commands-to-verify-and-troubleshoot): day-to-day checks, clean-up, common problems.

Conventions: every command is in a copyable block. The shell is named above each block: **PowerShell** for most commands and **Git Bash** only for the VPA install. Run everything from the repository root unless stated.

---

## 1. Installation and setup

### 1.1 What this project is

An internal **user management service**: a small REST API that creates, lists, updates and deletes user records. It must keep its data when Pods restart, be reachable at a friendly URL, and cope with busy periods without manual intervention.

```text
Browser / curl
   |  usermgmt-02230158.local  (hosts file -> 127.0.0.1, minikube tunnel)
   v
Ingress controller (ingress-nginx namespace)
   |  Ingress rule: host -> Service api
   v
Service api (ClusterIP :80)
   v
Deployment api (2-6 Pods, port 8000)  <-- HPA (50% CPU, 2-6 replicas)
   |  config: ConfigMap api-config, credentials: Secret postgres-secret
   v
Service postgres (headless, :5432)
   v
StatefulSet postgres (postgres-0)  <-- VPA (mode Off, recommendations only)
   v
PVC data-postgres-0 (1 Gi, StorageClass "standard")

metrics-server (kube-system) feeds CPU data to the HPA and the VPA.
```

### 1.2 What was implemented

| Milestone | Implementation |
|---|---|
| M1 Cluster and platform | minikube cluster (2 CPUs, 4 GB), ingress-nginx and metrics-server add-ons, VPA components, namespace from a manifest, default StorageClass identified |
| M2 Stateful database | PostgreSQL 16 as a StatefulSet (`postgres-0`), headless Service, Secret for credentials, `volumeClaimTemplates` (1 Gi PVC), requests and limits, persistence test |
| M3 Application | Flask REST API (7 endpoints), Dockerfile, versioned image `usermgmt-api:1.0`, ConfigMap + Secret, liveness and readiness probes, requests and limits, 2 replicas, ClusterIP Service |
| M4 Ingress | Ingress rule for `usermgmt-02230158.local`, hosts-file entry, `minikube tunnel`, wrong-host test |
| M5 Autoscaling | HPA (`autoscaling/v2`, 2-6 replicas, 50% CPU), VPA on the database in `Off` mode, load test with `hey`, 30-second timeline in `hpa-log.txt` |
| M6 Report and demo | Report, architecture diagram, troubleshooting account, this README |

### 1.3 Topics covered

Namespaces, StorageClass / PV / PVC, Secrets, ConfigMaps, StatefulSets, headless Services, Deployments and ReplicaSets, liveness and readiness probes, resource requests and limits, ClusterIP Services, Ingress and Ingress controllers, host-based routing, hosts file and `minikube tunnel`, metrics-server, HorizontalPodAutoscaler (v2), VerticalPodAutoscaler (`Off` mode) and why HPA and VPA must not act on the same workload, loading local images without a registry, load testing, troubleshooting with `describe`, events and logs, declarative deployment with `kubectl apply -f`.

### 1.4 File structure

```text
usermgmt/
├── README.md                          this file
├── install.ps1                        PowerShell helper used during installation/setup
├── hpa-log.txt                        30-second HPA and Pod-count timeline recorded during the load test
├── app/
│   ├── app.py                         Flask REST API (users CRUD, /healthz, /ready)
│   ├── Dockerfile                     builds usermgmt-api:1.0 (runs as non-root with gunicorn)
│   └── requirements.txt               pinned Python dependencies
└── k8s/                               numbered in the order they must be applied
    ├── 00-namespace.yaml              Namespace usermgmt-02230158
    ├── 01-postgres-secret.yaml        Secret: database name, user, password
    ├── 02-postgres-service.yaml       headless Service "postgres" (clusterIP: None)
    ├── 03-postgres-statefulset.yaml   StatefulSet postgres, 1 replica, 1 Gi PVC template
    ├── 04-api-configmap.yaml          ConfigMap api-config (DB host, port, name)
    ├── 05-api-deployment.yaml         Deployment api, 2 replicas, probes, requests/limits
    ├── 06-api-service.yaml            ClusterIP Service "api" (80 -> 8000)
    ├── 07-ingress.yaml                Ingress for usermgmt-02230158.local
    ├── 08-api-hpa.yaml                HPA api-hpa (2-6 replicas, 50% CPU)
    └── 09-postgres-vpa.yaml           VPA postgres-vpa (updateMode: Off)
```

### 1.5 Tools and versions

The versions below are the ones this project was built and tested with.

| Tool | Version used | Check command |
|---|---|---|
| OS | Windows 11 | |
| Docker Desktop | any recent version (4 GB or more memory available) | `docker --version` |
| minikube | v1.39.0 (Kubernetes v1.37.0, containerd runtime) | `minikube version` |
| kubectl | client v1.34.1 (prints a version-skew warning against v1.37.0; harmless for this project) | `kubectl version --client` |
| Git + Git Bash | any recent version (Git Bash ships `openssl`, needed by the VPA script) | `git --version` |
| hey | any recent version (load-testing tool) | `Get-Command hey` |

Install links (official pages): minikube (minikube.sigs.k8s.io/docs/start), kubectl (kubernetes.io/docs/tasks/tools), Git (git-scm.com), hey (github.com/rakyll/hey, download the Windows binary and put it on your PATH).

> `kind` is also allowed by the assignment. This project uses **minikube**, so no `kind` installation is needed.

### Step 1.5.1 Check the tools are installed

**What happens:** each command prints a version. If one prints "not recognized", install that tool first.

PowerShell:

```powershell
docker --version
minikube version
kubectl version --client
git --version
Get-Command hey
```

Expected: a version line for each, and `hey.exe` listed as an Application.

Git Bash (only to confirm `openssl` exists for the VPA script):

```bash
openssl version
```

Expected: `OpenSSL 3.x.x ...`

### Step 1.5.2 Make sure Docker is running

**What happens:** minikube runs its node inside a Docker container, so Docker Desktop must be running first. In Docker Desktop, allow at least 4 GB of memory (Settings, Resources).

```powershell
docker ps
```

Expected: a table (it may be empty). An error such as "cannot connect to the Docker daemon" means Docker Desktop is not running yet.

### 1.6 Start the cluster

**What happens:** minikube creates one Kubernetes node inside a Docker container with 2 CPUs and 4 GB memory.

```powershell
minikube start --driver=docker --cpus=2 --memory=4096
```

Expected (last lines):

```text
* Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
```

```powershell
kubectl get nodes
```

Expected:

```text
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   1m    v1.37.0
```

Optional: confirm the CPU and memory limits given to the node container:

```powershell
docker inspect minikube --format "{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}"
```

Expected: `2000000000 4294967296` (2 CPUs, 4 GiB).

### 1.7 Enable the add-ons

**What happens:** `metrics-server` collects CPU and memory use of every Pod (needed by `kubectl top` and the HPA). `ingress` installs the ingress-nginx controller, the Pod that receives web traffic and routes it by host name.

```powershell
minikube addons enable metrics-server
minikube addons enable ingress
```

Expected:

```text
* The 'metrics-server' addon is enabled
* The 'ingress' addon is enabled
```

Verify (wait a minute or two for the images to download):

```powershell
kubectl get pods -n ingress-nginx
kubectl get pods -n kube-system
kubectl get ingressclass
kubectl get storageclass
```

Expected:

```text
ingress-nginx-admission-create-xxxxx       0/1   Completed
ingress-nginx-admission-patch-xxxxx        0/1   Completed
ingress-nginx-controller-xxxxxxxxx-xxxxx   1/1   Running
...
metrics-server-xxxxxxxxxx-xxxxx            1/1   Running
...
nginx (default)      k8s.io/ingress-nginx
standard (default)   k8s.io/minikube-hostpath
```

The two `admission` Pods ending in `Completed` is correct. The controller must be `1/1 Running`.

> **If the controller stays `ContainerCreating` or `minikube addons enable ingress` times out:** the image download from `registry.k8s.io` is slow. Pre-pull the images inside the node, restart the Pods and enable the add-on again (the digests below are the ones this cluster used; if yours differ, read them from `kubectl describe pod -n ingress-nginx`):
>
> ```powershell
> minikube ssh -- sudo crictl --timeout=15m pull "registry.k8s.io/ingress-nginx/kube-webhook-certgen:v1.6.9@sha256:01038e7de14b78d702d2849c3aad72fd25903c4765af63cf16aa3398f5d5f2dd"
> minikube ssh -- sudo crictl --timeout=15m pull "registry.k8s.io/ingress-nginx/controller:v1.15.1@sha256:594ceea76b01c592858f803f9ff4d2cb40542cae2060410b2c95f75907d659e1"
> kubectl delete pod -n ingress-nginx --all
> minikube addons enable ingress
> ```

### 1.8 Install the Vertical Pod Autoscaler (VPA)

**What happens:** the VPA is installed from the official `kubernetes/autoscaler` repository. It adds three components in `kube-system` (recommender, updater, admission controller) and two CRDs. The install script is a **bash** script, so use **Git Bash** (not PowerShell). Clone the repository outside this project folder.

Git Bash:

```bash
cd ~
git clone --depth 1 -c core.autocrlf=false https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler
git fetch --depth 1 origin tag vertical-pod-autoscaler-1.8.0
```

*Why the extra `git fetch`:* a shallow clone has no tags, and `vpa-up.sh` checks out the release tag `vertical-pod-autoscaler-1.8.0`.

**Windows (Git Bash) only:** two workarounds were needed. Git Bash rewrites `/CN=...` into a Windows path, which breaks the certificate step, and the script writes certificates to `/tmp`. Run these before the install script:

```bash
sed -i 's|TMP_DIR="/tmp/vpa-certs"|TMP_DIR="./vpa-certs"|g' pkg/admission-controller/gencerts.sh
mkdir -p ./vpa-certs
export MSYS_NO_PATHCONV=1
```

Run the installer (all platforms):

```bash
./hack/vpa-up.sh
```

Expected (the last lines):

```text
Generating certs for the VPA Admission Controller in ./vpa-certs.
Certificate request self-signature ok
subject=CN=vpa-webhook.kube-system.svc
Uploading certs to the cluster.
secret/vpa-tls-certs created
Deleting ./vpa-certs.
```

There must be no `ERROR: Failed to create CA certificate` line. Verify (PowerShell):

```powershell
kubectl get pods -n kube-system | Select-String vpa
kubectl get crd | Select-String autoscaling
```

Expected:

```text
vpa-admission-controller-xxxxxxxxxx-xxxxx   1/1   Running
vpa-recommender-xxxxxxxxxx-xxxxx            1/1   Running
vpa-updater-xxxxxxxxxx-xxxxx                1/1   Running
verticalpodautoscalercheckpoints.autoscaling.k8s.io
verticalpodautoscalers.autoscaling.k8s.io
```

> **If a `vpa-*` Pod stays `ContainerCreating` or `ImagePullBackOff`:** pre-pull the images and restart the Deployments.
>
> ```powershell
> kubectl scale deployment vpa-updater vpa-recommender vpa-admission-controller -n kube-system --replicas=0
> minikube ssh -- sudo crictl --timeout=15m pull registry.k8s.io/autoscaling/vpa-updater:1.8.0
> minikube ssh -- sudo crictl --timeout=15m pull registry.k8s.io/autoscaling/vpa-recommender:1.8.0
> minikube ssh -- sudo crictl --timeout=15m pull registry.k8s.io/autoscaling/vpa-admission-controller:1.8.0
> kubectl scale deployment vpa-updater vpa-recommender vpa-admission-controller -n kube-system --replicas=1
> ```

### 1.9 Check metrics work

```powershell
kubectl top nodes
```

Expected: one line with CPU and memory numbers. If it says "Metrics API not available", wait a minute and run it again.

### 1.10 Get the project files

```powershell
git clone <your-repository-url> usermgmt
cd usermgmt
```

Replace `<your-repository-url>` with the repository link. If you already have the folder, just `cd` into it.

### 1.11 Optional: pre-pull the database image

**What happens:** downloads PostgreSQL once inside the node so the StatefulSet starts quickly even on a slow connection.

```powershell
minikube ssh -- sudo crictl --timeout=15m pull docker.io/library/postgres:16
```

Expected: `Image is up to date for sha256:...`

---

## 2. Apply and run (milestone by milestone)

All commands run from the repository root in **PowerShell**, with the cluster running (`kubectl get nodes` shows `Ready`) and Section 1 completed.

### 2.0 Quick path (everything at once)

**What happens:** builds and loads the image, then applies every manifest in numeric order. The milestone-by-milestone steps below explain each part and show the evidence.

```powershell
docker build -t usermgmt-api:1.0 ./app
minikube image load usermgmt-api:1.0
kubectl apply -f k8s/
```

Expected (after the build output):

```text
namespace/usermgmt-02230158 created
secret/postgres-secret created
service/postgres created
statefulset.apps/postgres created
configmap/api-config created
deployment.apps/api created
service/api created
ingress.networking.k8s.io/api-ingress created
horizontalpodautoscaler.autoscaling/api-hpa created
verticalpodautoscaler.autoscaling.k8s.io/postgres-vpa created
```

Then do the hosts-file and tunnel steps in Milestone 4 and wait until every Pod is `Running`:

```powershell
kubectl get pods -n usermgmt-02230158
```

---

### Milestone 1: Cluster and platform

**To do:** a running cluster with add-ons, the VPA, a namespace created from a manifest, and the default StorageClass identified. The cluster, add-ons and VPA were done in Section 1.

**Step M1.1 Create the namespace from the manifest**

*What happens:* a namespace is a named folder inside the cluster. Everything for this project lives in `usermgmt-02230158`.

```powershell
kubectl apply -f k8s/00-namespace.yaml
```

Expected:

```text
namespace/usermgmt-02230158 created
```

```powershell
kubectl get namespace usermgmt-02230158
```

Expected:

```text
NAME                STATUS   AGE
usermgmt-02230158   Active   5s
```

**Step M1.2 Identify the default StorageClass**

*What happens:* the default StorageClass creates disks automatically when a Pod asks for a PersistentVolumeClaim.

```powershell
kubectl get storageclass
```

Expected:

```text
NAME                 PROVISIONER                RECLAIMPOLICY   VOLUMEBINDINGMODE   ...
standard (default)   k8s.io/minikube-hostpath   Delete          Immediate           ...
```

Note: reclaim policy `Delete` means deleting a **PVC** deletes the data. Deleting a **Pod** does not.

---

### Milestone 2: Stateful database (PostgreSQL)

**To do:** a Secret for credentials, a headless Service, and a one-replica StatefulSet with its own 1 Gi PVC. Prove the data survives Pod deletion.

**Step M2.1 Apply the Secret, headless Service and StatefulSet**

*What happens:* the Secret holds the database name, user and password (nothing sensitive is in the StatefulSet file). The headless Service (`clusterIP: None`) gives the Pod a stable DNS name. The StatefulSet creates `postgres-0` and, through `volumeClaimTemplates`, a PVC named `data-postgres-0` that the `standard` StorageClass turns into a disk.

```powershell
kubectl apply -f k8s/01-postgres-secret.yaml
kubectl apply -f k8s/02-postgres-service.yaml
kubectl apply -f k8s/03-postgres-statefulset.yaml
```

Expected:

```text
secret/postgres-secret created
service/postgres created
statefulset.apps/postgres created
```

**Step M2.2 Wait until the database is ready**

```powershell
kubectl rollout status statefulset/postgres -n usermgmt-02230158 --timeout=300s
kubectl get statefulset,pod,pvc,pv -n usermgmt-02230158
```

Expected: the first command ends with a line saying the rolling update is complete. The second shows:

```text
statefulset.apps/postgres   1/1
pod/postgres-0              1/1   Running   0
persistentvolumeclaim/data-postgres-0   Bound   pvc-...   1Gi   RWO   standard
persistentvolume/pvc-...                1Gi     RWO   Delete   Bound   usermgmt-02230158/data-postgres-0   standard
```

**Step M2.3 Persistence test, part 1: insert a row**

*What happens:* `kubectl exec` runs `psql` inside the Pod to create a table and insert one row.

```powershell
kubectl exec -n usermgmt-02230158 postgres-0 -- psql -U appuser -d usersdb -c "CREATE TABLE persist_test (id serial PRIMARY KEY, note text);"
kubectl exec -n usermgmt-02230158 postgres-0 -- psql -U appuser -d usersdb -c "INSERT INTO persist_test (note) VALUES ('I survive pod deletion');"
kubectl exec -n usermgmt-02230158 postgres-0 -- psql -U appuser -d usersdb -c "SELECT * FROM persist_test;"
kubectl get pod postgres-0 -n usermgmt-02230158
```

Expected:

```text
CREATE TABLE
INSERT 0 1
 id |          note
----+------------------------
  1 | I survive pod deletion
(1 row)
NAME         READY   STATUS    RESTARTS   AGE
postgres-0   1/1     Running   0          5m
```

**Step M2.4 Persistence test, part 2: delete the Pod**

*What happens:* the StatefulSet notices the Pod is gone and creates a new `postgres-0`, re-attaching the same PVC.

```powershell
kubectl delete pod postgres-0 -n usermgmt-02230158
kubectl get pods -n usermgmt-02230158 -w
```

Expected: `pod "postgres-0" deleted`, then the Pod goes `ContainerCreating` and `Running 1/1`. Press `Ctrl+C` when it is `1/1 Running`.

**Step M2.5 Persistence test, part 3: the row is still there**

```powershell
kubectl get pod postgres-0 -n usermgmt-02230158
kubectl exec -n usermgmt-02230158 postgres-0 -- psql -U appuser -d usersdb -c "SELECT * FROM persist_test;"
```

Expected: the Pod's `AGE` is only seconds (a new Pod) and the same row `I survive pod deletion` is returned. If `exec` fails with a connection error, wait 20 seconds and retry.

Optional clean-up of the test table:

```powershell
kubectl exec -n usermgmt-02230158 postgres-0 -- psql -U appuser -d usersdb -c "DROP TABLE persist_test;"
```

---

### Milestone 3: User management application

**To do:** build the API image with a versioned tag, load it into the cluster, and run it as a Deployment with a ConfigMap, a Secret, probes, requests/limits and a ClusterIP Service.

**Step M3.1 Build the image and load it into minikube**

*What happens:* the image is built on your Docker, then copied into the minikube node (there is no registry). The Deployment uses `imagePullPolicy: IfNotPresent` so Kubernetes never tries to download it.

```powershell
docker build -t usermgmt-api:1.0 ./app
minikube image load usermgmt-api:1.0
minikube image ls | Select-String usermgmt
```

Expected: the build ends with a "naming to docker.io/library/usermgmt-api:1.0" line, and the last command prints `docker.io/library/usermgmt-api:1.0`.

If you rebuild with the same tag, remove the old copy first: `minikube image rm usermgmt-api:1.0`

**Step M3.2 Apply the ConfigMap, Deployment and Service**

*What happens:* the ConfigMap supplies the database host, port and name. The Secret supplies the user and password. The liveness probe checks `/healthz` (process alive, does not use the database). The readiness probe checks `/ready` (succeeds only if the database is reachable). The `api` Service load-balances across ready Pods on port 80, forwarding to container port 8000.

```powershell
kubectl apply -f k8s/04-api-configmap.yaml
kubectl apply -f k8s/05-api-deployment.yaml
kubectl apply -f k8s/06-api-service.yaml
kubectl rollout status deployment/api -n usermgmt-02230158 --timeout=180s
kubectl get deploy,rs,pods,svc -n usermgmt-02230158
```

Expected:

```text
configmap/api-config created
deployment.apps/api created
service/api created
deployment "api" successfully rolled out
```

and the listing shows `deployment.apps/api   2/2`, two `api-...` Pods `1/1 Running`, `postgres-0` `1/1 Running`, and `service/api   ClusterIP   ...   80/TCP`.

**Step M3.3 CRUD test through `kubectl port-forward`**

*What happens:* `port-forward` is a temporary tunnel from your laptop to the Service. It is only for testing the Service and Pods (Milestone 4 replaces it with the Ingress).

PowerShell window 1 (leave it running):

```powershell
kubectl port-forward svc/api 8080:80 -n usermgmt-02230158
```

Expected: `Forwarding from 127.0.0.1:8080 -> 8000`

PowerShell window 2. PowerShell strips quotes from JSON typed straight into `curl.exe`, so the JSON is written to files first:

```powershell
$b = "http://localhost:8080"
'{"name":"Tashi","email":"tashi@example.com"}' | Set-Content "$env:TEMP\u1.json" -Encoding ascii
'{"name":"Tashi D","email":"tashi@example.com"}' | Set-Content "$env:TEMP\u2.json" -Encoding ascii
curl.exe -i "$b/healthz"
curl.exe -i "$b/ready"
curl.exe -i -X POST "$b/users" -H "Content-Type: application/json" --data-binary "@$env:TEMP\u1.json"
curl.exe -i -X POST "$b/users" -H "Content-Type: application/json" --data-binary "@$env:TEMP\u1.json"
curl.exe -i "$b/users"
```

Then read the new user's id and use it for the remaining calls:

```powershell
$id = (Invoke-RestMethod "$b/users" | Where-Object { $_.email -eq "tashi@example.com" }).id
curl.exe -i "$b/users/$id"
curl.exe -i -X PUT "$b/users/$id" -H "Content-Type: application/json" --data-binary "@$env:TEMP\u2.json"
curl.exe -i -X DELETE "$b/users/$id"
curl.exe -i "$b/users/$id"
```

Expected status codes, in order:

| Call | Status |
|---|---|
| `GET /healthz` | `200 OK` `{"status":"ok"}` |
| `GET /ready` | `200 OK` `{"status":"ready"}` (database reachable) |
| `POST /users` | `201 CREATED` with the new user |
| `POST /users` (same email) | `409 CONFLICT` `{"error":"email already exists"}` |
| `GET /users` | `200 OK` list |
| `GET /users/{id}` | `200 OK` |
| `PUT /users/{id}` | `200 OK` (name changed) |
| `DELETE /users/{id}` | `204 NO CONTENT` |
| `GET /users/{id}` again | `404 NOT FOUND` |

`GET /` returns `404` by design: the API has no root page (only `/users`, `/users/{id}`, `/healthz`, `/ready`).

If you ran this test before, the first `POST` can return `409` because the user already exists. Use another email, or delete the old user first.

Add a few users for the load test in Milestone 5 (optional):

```powershell
97..116 | ForEach-Object { $c = [char]$_; Invoke-RestMethod -Uri "$b/users" -Method Post -ContentType "application/json" -Body "{`"name`":`"user $c`",`"email`":`"user$c@example.com`"}" | Out-Null }
```

**Step M3.4 Readiness test: the API depends on the database**

*What happens:* with the database stopped, `/ready` fails, so the `api` Pods become `0/1` and receive no traffic. They are **not restarted**, because `/healthz` does not use the database. This scale command is a temporary experiment for evidence. The manifests still say `replicas: 1`.

```powershell
kubectl scale statefulset postgres -n usermgmt-02230158 --replicas=0
kubectl get pods -n usermgmt-02230158 -w
```

Expected: `postgres-0` terminates and, after roughly 15 seconds, both `api` Pods show `0/1` with `RESTARTS` still `0`. Press `Ctrl+C`, then bring the database back:

```powershell
kubectl scale statefulset postgres -n usermgmt-02230158 --replicas=1
kubectl get pods -n usermgmt-02230158 -w
```

Expected: `postgres-0` returns to `1/1 Running`, then the `api` Pods return to `1/1`. Press `Ctrl+C`. The users created earlier are still there (the PVC was never touched).

---

### Milestone 4: Ingress

**To do:** route the host name `usermgmt-02230158.local` to the `api` Service through an Ingress, reach it from the host machine, and show another host name does not reach the app.

**Step M4.1 Apply the Ingress**

*What happens:* the Ingress object is only configuration. The ingress-nginx controller Pod watches it and routes requests whose `Host` header is `usermgmt-02230158.local` to Service `api` port 80. The manifest sets `ingressClassName: nginx`.

```powershell
kubectl apply -f k8s/07-ingress.yaml
kubectl get ingress -n usermgmt-02230158
```

Expected:

```text
ingress.networking.k8s.io/api-ingress created

NAME          CLASS   HOSTS                     ADDRESS        PORTS   AGE
api-ingress   nginx   usermgmt-02230158.local   192.168.49.2   80      1m
```

The `ADDRESS` can take a minute to appear. If you ever switch to the traefik add-on, change `ingressClassName` to `traefik`.

**Step M4.2 Add the host name to the hosts file**

*What happens:* your computer must know that `usermgmt-02230158.local` means "this machine, where the tunnel enters the cluster".

Check whether the line already exists:

```powershell
Select-String "usermgmt-02230158" C:\Windows\System32\drivers\etc\hosts
```

If it prints nothing, add it. Open PowerShell **as Administrator**:

```powershell
Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "127.0.0.1 usermgmt-02230158.local" -Encoding ascii
```

Expected: the check command now prints `127.0.0.1 usermgmt-02230158.local`.

| Your setup | Hosts-file address |
|---|---|
| Windows or macOS with Docker Desktop (this project) | `127.0.0.1`, with `minikube tunnel` running |
| Linux with the docker driver | the output of `minikube ip` (for example `echo "$(minikube ip) usermgmt-02230158.local" \| sudo tee -a /etc/hosts`) |

**Step M4.3 Start the tunnel**

*What happens:* on Windows and macOS the minikube node lives inside a Docker container, so `minikube tunnel` bridges your computer to the cluster's ingress at `127.0.0.1`. It is not a port-forward, but it must stay open.

Open a separate PowerShell window **as Administrator** and leave it running:

```powershell
minikube tunnel
```

Expected: the window stays open and prints tunnel status lines. Do not close it while testing.

**Step M4.4 Test through the host name**

```powershell
curl.exe -i http://usermgmt-02230158.local/users
curl.exe -i -H "Host: other.local" http://127.0.0.1/users
kubectl describe ingress api-ingress -n usermgmt-02230158
```

Expected:

- The first command returns `200 OK` with the JSON user list.
- The second returns `404 Not Found` from **nginx** (the controller found no rule for `other.local`). The response must not contain any user data.
- `describe` shows host `usermgmt-02230158.local`, path `/`, and backend `api:80` with Pod addresses like `10.244.x.x:8000`.

(A Flask-style 404, "The requested URL was not found on the server", would mean the request reached the app. An nginx 404 means the Ingress did not match.)

**Request path (for the report):** client resolves the name through the hosts file, then reaches the Ingress controller Pod, which matches the `Host` header against the Ingress rules, then forwards to Service `api`, which picks one Ready Pod and sends the request to port 8000, and the response returns the same way.

---

### Milestone 5: Autoscaling (metrics-server, HPA, VPA)

**To do:** confirm metrics work, create an HPA for the API (2-6 replicas, 50% CPU) and a VPA for the database (`Off` mode), generate load through the Ingress, and record the timeline.

**Step M5.1 Confirm metrics**

```powershell
kubectl top pods -n usermgmt-02230158
```

Expected: CPU and memory for the `api` Pods and `postgres-0`. Wait a minute if it says metrics are not available yet.

**Step M5.2 Apply the HPA and VPA**

*What happens:* the HPA compares the average CPU use of the `api` Pods with their CPU **request** (100m) every ~15 seconds and adds Pods when it is above 50%, up to 6. The VPA watches the database and only **recommends** resources (`updateMode: "Off"`), it never changes or restarts the database.

```powershell
kubectl apply -f k8s/08-api-hpa.yaml
kubectl apply -f k8s/09-postgres-vpa.yaml
kubectl get hpa -n usermgmt-02230158
```

Expected:

```text
horizontalpodautoscaler.autoscaling/api-hpa created
verticalpodautoscaler.autoscaling.k8s.io/postgres-vpa created

NAME      REFERENCE        TARGETS       MINPODS   MAXPODS   REPLICAS
api-hpa   Deployment/api   cpu: 3%/50%   2         6         2
```

`<unknown>/50%` for under a minute right after creation is normal.

**Step M5.3 Pre-flight check**

Before the load test, make sure `replicas` is back at 2, the call below returns `200`, and `minikube tunnel` is still running:

```powershell
kubectl get hpa api-hpa -n usermgmt-02230158
curl.exe -s -o NUL -w "%{http_code}" http://usermgmt-02230158.local/users
```

**Step M5.4 Record the timeline (window A)**

*What happens:* writes one snapshot of the HPA and the Pods every 30 seconds to the screen and to `hpa-log.txt`. Start it first and leave 2-3 samples as the baseline.

```powershell
while ($true) {
  $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $hpa  = kubectl get hpa api-hpa -n usermgmt-02230158
  $pods = kubectl get pods -n usermgmt-02230158 -l app=api --no-headers
  $block = @("--- $ts ---") + $hpa + $pods + @("Pods listed: $(@($pods).Count)", "")
  $block
  $block | Out-File hpa-log.txt -Append -Encoding ascii
  Start-Sleep -Seconds 30
}
```

**Step M5.5 Generate load (window B)**

```powershell
hey -z 3m -c 50 http://usermgmt-02230158.local/users
```

Expected: after 3 minutes a summary with a `Status code distribution`. Most responses should be `[200]`. Some `[500]` or `[503]` responses can appear while the database is saturated and new Pods are starting.

Expected in window A: CPU rises well above 50%, `REPLICAS` climbs (for example 2, then 4, then 6), stays at 6 for about 5 minutes after the load stops (the HPA's default scale-down stabilisation window is 300 seconds), then falls back to 2. Keep recording until 2-3 samples show 2 replicas, then press `Ctrl+C` in window A.

Right after the load ends, capture the scaling events:

```powershell
kubectl describe hpa api-hpa -n usermgmt-02230158
```

Expected events (times differ):

```text
SuccessfulRescale   New size: 4; reason: cpu resource utilization (percentage of request) above target
SuccessfulRescale   New size: 6; reason: cpu resource utilization (percentage of request) above target
SuccessfulRescale   New size: 2; reason: All metrics below target
```

**Step M5.6 Read the VPA recommendation**

*What happens:* the recommender builds an estimate from observed usage. Wait 5-10 minutes after the load test.

```powershell
kubectl get vpa -n usermgmt-02230158
kubectl describe vpa postgres-vpa -n usermgmt-02230158
```

Expected: a `Recommendation` section with `Lower Bound`, `Target`, `Uncapped Target` and `Upper Bound` for CPU and memory of the `postgres` container. If it is empty, wait longer and look at the `Conditions` section.

**Why the VPA is on the database, in `Off` mode (short):** the HPA scales the API on CPU use, which is usage divided by the CPU request. A VPA that also changed the API's CPU request would change that divisor, and the two would keep reacting to each other. The database is a single replica that cannot be scaled out by an HPA, so vertical sizing is the right tool. `Off` only recommends, because the active modes work by evicting the Pod, which for the only database Pod means downtime. The HPA acts only on `api`, the VPA only on `postgres`, so they never touch the same workload.

---

### Milestone 6: Report and demonstration

**To do:** a short report (maximum 8 pages excluding the manifest appendix) with the architecture diagram, evidence for each milestone and one real problem with how it was diagnosed; then a live demo of up to 10 minutes.

Checklist:

- Architecture diagram matches what was deployed (names in this README).
- State which Ingress controller was used: **ingress-nginx** via the minikube `ingress` add-on.
- Evidence for each milestone from Section 3.
- One real problem and its diagnosis with the commands used (Section 4 lists the ones met in this project).
- Before submitting, run the fresh-cluster test below and keep this README exact.

**Fresh-cluster test (proves this README works)**

```powershell
kubectl delete namespace usermgmt-02230158
```

Then repeat Section 1 (cluster, add-ons, VPA) on a clean cluster if you want the full test (`minikube delete`, then `minikube start ...`), followed by:

```powershell
docker build -t usermgmt-api:1.0 ./app
minikube image load usermgmt-api:1.0
kubectl apply -f k8s/
kubectl get pods -n usermgmt-02230158
```

Expected: `postgres-0` and two `api` Pods `1/1 Running`, and `curl.exe -i http://usermgmt-02230158.local/users` returns `200`.

---

## 3. Evidence checks (milestone by milestone)

Run these to prove each milestone works and take screenshots of the output (or save it, for example `kubectl get nodes | Tee-Object evidence-m1-nodes.txt`). The part to look for is listed under each block. Replace nothing: the namespace is already `usermgmt-02230158`.

### Evidence M1: Cluster and platform

```powershell
kubectl get nodes
kubectl get pods -A
kubectl get storageclass
kubectl top nodes
kubectl get namespace usermgmt-02230158
kubectl describe node minikube | Select-String "cpu:|memory:"
```

Look for:

- `get nodes`: node `minikube` `Ready`.
- `get pods -A`: the ingress-nginx controller, `metrics-server` and `vpa-admission-controller`, `vpa-recommender`, `vpa-updater` all `Running`. Put them in one screenshot.
- `get storageclass`: `standard (default)` with provisioner `k8s.io/minikube-hostpath`.
- `top nodes`: CPU and memory values (not an error).
- `get namespace`: `usermgmt-02230158` `Active`.
- `describe node`: Capacity of at least 2 CPUs and about 4 GB of memory.

### Evidence M2: Stateful database

```powershell
kubectl get statefulset,pod,pvc,pv -n usermgmt-02230158
kubectl get svc,secret -n usermgmt-02230158
kubectl describe pvc data-postgres-0 -n usermgmt-02230158
Select-String -Path k8s\03-postgres-statefulset.yaml -Pattern "secretRef" -Context 0,2
Select-String -Path k8s\03-postgres-statefulset.yaml -Pattern "PASSWORD"
```

Look for:

- `postgres-0` `1/1 Running` (the stable name), and PVC `data-postgres-0` `Bound`, at least `1Gi`, class `standard`, with a matching PV.
- Service `postgres` with `CLUSTER-IP` `None` (headless) and the Secret `postgres-secret`.
- `describe pvc`: `Status: Bound`, `StorageClass: standard`, and `Used By: postgres-0`.
- The `secretRef` search shows the StatefulSet reads credentials from `postgres-secret`. The `PASSWORD` search prints **nothing**, proving no password is in the StatefulSet manifest.
- The persistence test as a sequence: Step M2.3 (before), M2.4 (deletion), M2.5 (after).

### Evidence M3: Application

```powershell
kubectl get deploy,rs,pods,svc -n usermgmt-02230158
kubectl describe deployment api -n usermgmt-02230158 | Select-String "Image:|Replicas:|Liveness|Readiness|Limits|Requests|cpu|memory"
kubectl exec -n usermgmt-02230158 deploy/api -- env | Select-String "^DB_(HOST|PORT|NAME|USER)="
kubectl get configmap api-config -n usermgmt-02230158 -o yaml
Select-String -Path k8s\05-api-deployment.yaml -Pattern "secretKeyRef" -Context 0,3
Select-String -Path k8s\05-api-deployment.yaml -Pattern ":latest"
minikube image ls | Select-String usermgmt
```

Look for:

- `api` `2/2`, two `1/1 Running` Pods, `service/api` of type `ClusterIP`.
- Image `usermgmt-api:1.0` (a versioned tag), 2 replicas, liveness on `/healthz`, readiness on `/ready`, and CPU/memory requests and limits.
- `DB_HOST=postgres`, `DB_PORT=5432`, `DB_NAME=usersdb`, `DB_USER=appuser`. Do **not** print or screenshot `DB_PASSWORD`.
- The password comes from `secretKeyRef` (the `:latest` search prints nothing, so no `latest` tag).
- The CRUD results: Step M3.3 (all endpoints, with the port-forward window visible).
- The readiness test: Step M3.4 (`api` Pods `0/1` with `RESTARTS` unchanged while the database is down).

### Evidence M4: Ingress

Close any `kubectl port-forward` window first, so only the Ingress path is tested. Keep `minikube tunnel` running.

```powershell
kubectl get ingress -n usermgmt-02230158
kubectl describe ingress api-ingress -n usermgmt-02230158
Select-String "usermgmt-02230158" C:\Windows\System32\drivers\etc\hosts
curl.exe -i http://usermgmt-02230158.local/users
curl.exe -i -H "Host: other.local" http://127.0.0.1/users
```

Look for:

- Ingress `api-ingress`, class `nginx`, host `usermgmt-02230158.local`.
- `describe`: path `/`, backend `api:80` with Pod addresses.
- The hosts-file line `127.0.0.1 usermgmt-02230158.local`.
- The `200 OK` response with user JSON through the host name (no `localhost:8080`).
- The `404` from nginx for `other.local`, with no user data.

### Evidence M5: Autoscaling

```powershell
kubectl top pods -n usermgmt-02230158
kubectl get hpa api-hpa -n usermgmt-02230158
kubectl describe hpa api-hpa -n usermgmt-02230158
Get-Content k8s\08-api-hpa.yaml
Get-Content k8s\09-postgres-vpa.yaml
Select-String -Path hpa-log.txt -Pattern "^---|api-hpa" | ForEach-Object { $_.Line }
kubectl get vpa -n usermgmt-02230158
kubectl describe vpa postgres-vpa -n usermgmt-02230158
```

Look for:

- `top pods`: metrics for the `api` Pods and `postgres-0`.
- The HPA manifest: `autoscaling/v2`, `minReplicas: 2`, `maxReplicas: 6`, CPU `averageUtilization: 50`.
- `describe hpa` events: `New size: 4`, `New size: 6`, then later `New size: 2`.
- The `hpa-log.txt` extract: a timestamp line followed by an `api-hpa` line (CPU% and `REPLICAS`) every 30 seconds. Turn it into a table of elapsed time, CPU% and replicas. It must show the climb from 2 to 6 **and** the return to 2.
- The VPA manifest: `updateMode: "Off"` and target `StatefulSet/postgres`.
- `describe vpa`: Lower Bound, Target and Upper Bound.
- Load-test settings to state in the report: `hey -z 3m -c 50 http://usermgmt-02230158.local/users` through the Ingress host.

### Evidence M6: Report and repository

```powershell
tree /F
git status
git log --oneline
```

Look for:

- The tree matches Section 1.4, and the manifests in `k8s/` are numbered in apply order.
- `git status` is clean and `git log` shows your commits.
- The report has the architecture diagram, the evidence above, one real troubleshooting account, and the manifests as an appendix.

---

## 4. Other commands to verify and troubleshoot

### 4.1 One-look overview

```powershell
kubectl get all,configmap,secret,pvc,ingress,hpa,vpa -n usermgmt-02230158
kubectl get pods -n usermgmt-02230158 -o wide
kubectl get events -n usermgmt-02230158 --sort-by=.lastTimestamp
```

### 4.2 Logs and details

```powershell
kubectl logs deploy/api -n usermgmt-02230158 --tail=30
kubectl logs postgres-0 -n usermgmt-02230158 --tail=30
kubectl logs <pod-name> -n usermgmt-02230158 --previous
kubectl describe pod <pod-name> -n usermgmt-02230158
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --tail=30
```

`--previous` shows the log of a container before it restarted. Replace `<pod-name>` with a name from `kubectl get pods`.

### 4.3 Look inside the database

```powershell
kubectl exec -n usermgmt-02230158 postgres-0 -- psql -U appuser -d usersdb -c "\dt"
kubectl exec -n usermgmt-02230158 postgres-0 -- psql -U appuser -d usersdb -c "SELECT count(*) FROM users;"
```

### 4.4 Restart and roll out

```powershell
kubectl rollout restart deployment/api -n usermgmt-02230158
kubectl rollout status deployment/api -n usermgmt-02230158
kubectl get hpa api-hpa -n usermgmt-02230158 -w
```

### 4.5 After a reboot, sleep or Docker restart

```powershell
minikube status
minikube start
kubectl get nodes
kubectl get pods -A
```

Use plain `minikube start` (not `delete`): it keeps the namespace, data, add-ons and loaded images. Restart `minikube tunnel` in an Administrator window afterwards.

### 4.6 Stop and clean up

```powershell
minikube stop
```

Stops the cluster and keeps everything. To remove the application only (this deletes the database data):

```powershell
kubectl delete namespace usermgmt-02230158
```

To remove the whole cluster (everything, including the loaded image and the VPA install):

```powershell
minikube delete
```

Optionally remove the hosts-file line (Administrator PowerShell):

```powershell
(Get-Content C:\Windows\System32\drivers\etc\hosts) | Where-Object { $_ -notmatch "usermgmt-02230158.local" } | Set-Content C:\Windows\System32\drivers\etc\hosts
```

### 4.7 Save the work

```powershell
git add -A
git commit -m "Update usermgmt manifests, README and logs"
```

### 4.8 Common problems and how they were diagnosed

| Symptom | Check | Cause and fix |
|---|---|---|
| `Unable to connect to the server ... connection refused` | `minikube status` | The cluster is stopped (Docker restarted, laptop slept). Run `minikube start`. |
| Ingress controller stuck `ContainerCreating`; event `secret "ingress-nginx-admission" not found` | `kubectl get events -n ingress-nginx --sort-by=.lastTimestamp`, `kubectl get jobs -n ingress-nginx` | The controller mounts a certificate Secret that the `admission-create` Job makes. That Job was stuck pulling its image. Pre-pull the images (Section 1.7), delete the Pods, enable the add-on again. |
| `vpa-up.sh` prints `fatal: invalid reference: vertical-pod-autoscaler-1.8.0` | `git tag` | A shallow clone has no tags. Run `git fetch --depth 1 origin tag vertical-pod-autoscaler-1.8.0` (Section 1.8). |
| `vpa-up.sh` prints `This name is not in that format: 'C:/Program Files/Git/CN=...'` | | Git Bash rewrites `/CN=` as a Windows path. Run `export MSYS_NO_PATHCONV=1` first (Section 1.8). |
| `vpa-*` Pod `ContainerCreating` or `ImagePullBackOff` | `kubectl describe pod -n kube-system <vpa-pod>` | Slow or stalled registry download. Pre-pull with `crictl` (Section 1.8). |
| `ErrImagePull` / `ErrImageNeverPull` on `api` | `kubectl describe pod <api-pod> -n usermgmt-02230158` | The image is not in the node. Run `minikube image load usermgmt-api:1.0`. |
| `400 name and email are required` from PowerShell `curl.exe` | | PowerShell strips the quotes in inline JSON. Write the JSON to a file and use `--data-binary "@file.json"` (Step M3.3), or use `Invoke-RestMethod`. |
| `GET /` returns "Not Found" | | Expected. The API has no root page. Use `/users`. |
| `no such host` / `Could not resolve host` | `Select-String "usermgmt-02230158" C:\Windows\System32\drivers\etc\hosts` | Hosts-file line missing, or `<sid>` was typed literally instead of `02230158`. |
| Connection refused or timeout on `usermgmt-02230158.local` | | `minikube tunnel` is not running (or not as Administrator). Start it (Step M4.3). |
| HPA `TARGETS` shows `<unknown>` | `kubectl top pods -n usermgmt-02230158` | metrics-server is not ready yet, or the Pods have no CPU request. Wait a minute, or check Section 1.7 and 1.9. |
| Many `503` or `500` during the load test | `kubectl top pods -n usermgmt-02230158`, `kubectl describe pod <api-pod> -n usermgmt-02230158` | The database is near its CPU limit, and slow responses can fail the probes while new Pods start. This is what the VPA recommendation for the database is about. |

---

*Student 02230158. All manifests are in `k8s/` and applied with `kubectl apply -f`. Imperative commands were used only to observe the cluster and for the temporary readiness experiment in Step M3.4.*
