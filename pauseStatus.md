# Private Reading — Pause Status

## What Is This

A private audiobook service. User pastes text → Fish TTS converts it to Opus audio → user downloads from a pre-signed OCI URL.

Architecture: Static SPA on OCI Object Storage → OCI API Gateway (JWT auth) → OCI Function (Python) → OCI NoSQL Database. Home k3s cluster polls the API as a pull-based worker, runs Fish TTS, uploads the result to OCI Object Storage.

---

## Done

### Phase 1 — Local Frontend (complete)
- FastAPI server on port 7860 (`app.py`, `main.py`)
- Dark-themed SPA; prompt injection check before TTS submission
- Direct Fish TTS pipeline integration (binary WAV → Opus via ffmpeg)
- Entry point: `python main.py` or `uvicorn app:app --port 7860`

### Phase 2 — Cloud Infrastructure + OCI Function (complete)

#### Terraform State
- Backend: HCP Terraform Cloud, org `SyntacticallySugary`, workspace `private-reading`, CLI-driven, local execution
- Credentials at `~/.terraform.d/credentials.tfrc.json`

#### Deployed Resources

| Resource | Name / ID |
|---|---|
| OCI region | us-chicago-1 |
| OCI namespace | axwer8ojpvgx |
| OCI compartment | (root tenancy OCID) |
| VCN | private-reading-prod-vcn |
| Private subnet | for Functions app |
| Public subnet + IGW | for API Gateway |
| OCI Object Storage — web | private-reading-prod-web |
| OCI Object Storage — audio | private-reading-prod-audiobooks |
| OCI NoSQL table | private_reading_prod_jobs |
| Cognito User Pool | us-east-1_Bg1FA4097 (shared, owned by Know-It-All CloudFormation) |
| Cognito app client | 7lkv9uvo8e8f47gepa7fg7rbb9 |
| OCI Functions app | private-reading-prod-app |
| OCI Function | private-reading-prod-api |
| OCIR image | ord.ocir.io/axwer8ojpvgx/private-reading/api:latest |
| API Gateway | private-reading-prod-gateway |
| API deployment | private-reading-prod-deployment |

#### Live Endpoints
```
API base URL:   https://o35eybtgc6wg5jujhe5xeixioe.apigateway.us-chicago-1.oci.customer-oci.com/v1
Cognito issuer: https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Bg1FA4097
JWKS URI:       https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Bg1FA4097/.well-known/jwks.json
```

#### API Routes (all live)
| Route | Method | Auth |
|---|---|---|
| /v1/jobs | POST | Cognito JWT (AUTHENTICATION_ONLY at gateway) |
| /v1/jobs/current | GET, DELETE | Cognito JWT |
| /v1/jobs/current/url | GET | Cognito JWT |
| /v1/worker/jobs/pending | GET | ANONYMOUS at gateway; X-Worker-Token validated in function |
| /v1/worker/jobs/{id}/claim | POST | same |
| /v1/worker/jobs/{id}/complete | POST | same |
| /v1/worker/jobs/{id}/fail | POST | same |

#### NoSQL Schema
Table: `private_reading_prod_jobs`
```
PRIMARY KEY (SHARD(user_id), job_id)
Columns: user_id, job_id, status, text, text_length, created_at, updated_at, error, audio_path, audio_expires_at
Status values: pending → processing → complete | failed
```

#### Function Code
`fn/func.py` — single Python file, all routes, resource principal auth to OCI NoSQL + Object Storage, JWT decoded from Bearer header (gateway validates sig), worker routes guarded by `X-Worker-Token`.

#### Terraform Quirks Discovered
- OCI provider v8.x uses `public_keys { }` not `validation_policy { }` for API Gateway JWT auth
- Per-route authorization for JWT-protected routes is `AUTHENTICATION_ONLY`, not `JWT_AUTHENTICATION`
- `issuers` and `audiences` are direct fields on the `authentication` block
- `count` on API Gateway deployment depends on function OCID → requires two-step `terraform apply` on first deploy (first `-target` the function, then apply normally)
- OCIR Docker login with special-char auth tokens: write base64 credentials directly to `~/.docker/config.json` rather than using `docker login`

---

## Phase 3 — k3s Worker (complete)
The home worker that polls the cloud API and runs Fish TTS.

**Implemented:**
- `worker/worker.py`: Polling loop, job claiming, async TTS processing (aiohttp), and OCI Object Storage upload via `run_in_executor`.
- `worker/requirements.txt`: Dependencies including `oci`, `aiohttp`, and pipeline requirements.
- `worker/Dockerfile`: Container image with `ffmpeg` and `libopus`.
- `worker/k8s/`: Kubernetes manifests for deployment on the k3s cluster.
  - `deployment.yaml`: CPU/memory resource limits; no GPU dependency (worker calls Fish TTS over HTTP).
  - `configmap.yaml`: API endpoints, OCI metadata, Fish TTS cluster DNS endpoint.
  - `secret.yaml.example`: Templates for worker tokens and OCI credentials.
  - `fish-tts-service.yaml`: ClusterIP Service exposing Fish TTS pods at port 8013.

**Still needed:**
- Deploy the Fish TTS pod to sparky (DGX Spark node) with `nodeSelector: kubernetes.io/hostname: sparky` and GPU resources — that deployment is separate from the worker.
- Apply all k8s manifests to the cluster.
- Build and push the worker Docker image to OCIR.

---

## Phase 4 — Frontend SPA (complete)
Static HTML/CSS/JS — no build toolchain, directly uploadable to OCI Object Storage.

**Implemented:**
- `spa/index.html`: Main UI with authentication and job submission.
- `spa/style.css`: Dark-themed styling matching Phase 1.
- `spa/app.js`: Cognito PKCE flow, OCI API integration, and job status polling.
  - `COGNITO_DOMAIN`: `https://private-reading-prod.auth.us-east-1.amazoncognito.com`

**Still needed:**
- Run `terraform apply` to provision `aws_cognito_user_pool_domain` (domain prefix `private-reading-prod`) — login is broken until this applies.
- Upload SPA files to the OCI web bucket.

---

## Phase 5 — CI/CD (Gitea Actions) (complete)
**Implemented:**
- `.gitea/workflows/deploy-function.yml`: Automated OCIR push and OCI Function update.
- `.gitea/workflows/deploy-spa.yml`: Automated SPA sync to OCI Object Storage.
- `.gitea/workflows/deploy-worker.yml`: Automated worker image build and K8s rollout.
- `.gitea/workflows/terraform.yml`: Infrastructure as Code pipeline via HCP Terraform.

---

## Remaining Before Live

1. **`terraform apply`** — provisions `aws_cognito_user_pool_domain` (`private-reading-prod`). This unblocks SPA login.
2. **Deploy Fish TTS pod** to sparky with GPU resources and label `app: fish-tts`. (Separate deployment, not in this repo.)
3. **Apply k8s manifests** — namespace, configmap, secrets, fish-tts-service, worker deployment.
4. **Build and push worker image** — `docker build` + push to `ord.ocir.io/axwer8ojpvgx/private-reading/worker:latest`.
5. **Upload SPA** to `private-reading-prod-web` OCI bucket with public read.

---

## Key Credentials (not committed)

| Secret | Location |
|---|---|
| terraform.tfvars | `/home/jimbob/Dev/myaudible/terraform/terraform.tfvars` (gitignored) |
| HCP Terraform token | `~/.terraform.d/credentials.tfrc.json` |
| OCIR auth token | `~/.docker/config.json` (key `ord.ocir.io`) |
| OCI API key | `~/.oci/config` |
| Worker API key | in terraform.tfvars; goes into k8s Secret |
