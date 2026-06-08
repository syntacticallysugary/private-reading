# Private Reading

A hybrid cloud/on-premises audiobook service. Paste text in a web app, get an Opus audio file back. Built as a portfolio demonstration of cloud-native architecture with on-premises GPU inference.

---

## Architecture

```
Browser
  │  JWT (AWS Cognito)
  ▼
OCI API Gateway
  │  Routes & auth
  ▼
OCI Functions (serverless)         OCI NoSQL (job store)
  │  POST /jobs → job_id           OCI Object Storage (audio)
  │  GET  /jobs/{id} → status      │
  │  GET  /jobs/{id}/download → pre-signed URL
  │
  │  POST /notify (webhook via WireGuard VPN)
  ▼
On-premises k3s worker  ────────▶  Qwen3-TTS-Base (GPU)
  │  claim → chunk → TTS → stitch
  ▼
OCI Object Storage (Opus audio)
  │  pre-signed URL
  ▼
Browser downloads file
```

The worker runs permanently in a home-lab k3s cluster. When a job is submitted, the OCI Function sends a webhook notification to the worker over a WireGuard VPN tunnel, waking it immediately. The worker also polls the cloud API on a fallback interval in case the webhook is missed. Processing runs on a local GPU and results are stored in OCI Object Storage.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Identity | AWS Cognito (USER_PASSWORD_AUTH native flow, no redirect) |
| API | OCI API Gateway → OCI Functions (Python, fdk) |
| Job store | OCI NoSQL (borneo SDK) |
| Audio storage | OCI Object Storage (pre-signed URLs) |
| TTS inference | Qwen3-TTS-12Hz-1.7B-Base via faster-qwen3-tts |
| Worker runtime | k3s (Kubernetes) on-premises, pulls image from OCIR |
| Job delivery | WireGuard VPN (OCI → home lab) + aiohttp webhook receiver; polling fallback |
| IaC | Terraform (VCN, Functions, NoSQL, API Gateway, Cognito app client) |
| CI/CD | Gitea Actions (4 workflows: terraform, deploy-function, deploy-worker, deploy-spa) |
| Container registry | OCI Container Registry (OCIR) |
| SPA | Vanilla JS, served from OCI Object Storage |
| Security scanning | TruffleHog · Bandit · Checkov · pip-audit (pre-commit + CI) |

---

## Repository Layout

```
fn/                     OCI Function — serverless API handler
  func.py               All routes: /jobs, /voice, /worker/*
  func.yaml             OCI Function deployment manifest

worker/
  worker.py             Polling worker: claim → chunk → TTS → stitch
  Dockerfile            Runs as UID 1000; HEALTHCHECK via pgrep
  k8s/                  Kubernetes manifests (Deployment, ConfigMap, Secrets)

private_reading/
  core/
    chunk_manager.py    Paragraph-aware semantic chunking (semchunk)
    tts_client.py       Async TTS client, Fish and Qwen providers
    audio_stitcher.py   ffmpeg WAV concatenation + Opus encoding
    text_extractor.py   Markdown / TXT / DOCX / PDF extraction
  config.py             Pydantic settings, env-var driven

spa/
  index.html            Single-page app (login, convert, status, download)
  app.js                Cognito USER_PASSWORD_AUTH, job polling, audio download
  style.css             Dark-navy design

terraform/              VCN, Functions, NoSQL, Object Storage, API Gateway, Cognito

.gitea/workflows/       CI/CD: security scans, SPA deploy, worker image, terraform
```

---

## Key Design Decisions

**How does the cloud reach an on-premises node behind NAT?**
A WireGuard VPN tunnel connects the OCI ARM VM (`erpnext-free`) to the home-lab ER605 router as a persistent peer. OCI's VCN routes the home-lab subnet through the VM's VNIC, so OCI Functions can POST a webhook directly to the worker at its LAN IP the moment a job is created. The worker also polls on a 10-second fallback in case the webhook is not delivered.

**Why OCI Functions over a persistent server?**
The API handles bursty traffic (user submits → waits → downloads). Serverless eliminates idle capacity and scales to zero between jobs.

**Why Qwen3-TTS-Base over Fish Speech?**
Qwen3-TTS-12Hz-1.7B-Base is SOTA open-source English TTS (1.24% WER on Seed-TTS). It generates a 400-character chunk in ~30s on the test hardware, roughly 7× faster than Fish Speech on the same machine. The ICL voice cloning API (`/v1/references/add`) is compatible with Fish's reference API, allowing a drop-in swap.

**Text preprocessing**
PDF extraction produces artifacts (citation brackets, arXiv/DOI identifiers, URLs, footnote symbols) that TTS reads verbatim. `ChunkManager._clean()` strips these before chunking so the audio sounds natural.

**JWT validation without a network call**
The OCI Function runs in a private subnet with no NAT gateway. Cognito's public JWKs are embedded directly in `func.py` and verified locally, eliminating the outbound call to the Cognito JWKS endpoint on every request.

---

## Known Shortcomings

The current pipeline accepts pasted plain text. Scientific and technical documents copied from PDFs contain structures that degrade or break TTS output:

**Two-column layout bleed** — PDF extractors read columns linearly, interleaving half-sentences from the left and right columns. No amount of text cleanup can fix this; it requires layout-aware PDF parsing.

**Tables** — Copied table rows arrive as whitespace-separated strings with no spoken structure. The TTS reads them as a run of numbers and abbreviations with no context. Statistical notation (`t(49.1) = 0.022, p = 0.983`) and column headers embedded mid-text compound the problem.

**Equations** — Inline math gets split across lines by the PDF extractor (e.g., `I²R` becomes `I`, newline, `2`, newline, `R`). Equation numbers `(1)` are read aloud. `ChunkManager._clean()` and `_normalize()` handle the most common cases but cannot reconstruct the semantic intent of complex expressions.

**Running headers and footers** — Journal name, paper title, and author list repeat on every page and land mid-paragraph in the extracted text. The current footer heuristics catch common patterns but journal-specific formats vary.

**Ligatures** — Typographic ligatures (`ﬁ`, `ﬂ`, `ﬃ`) may survive as single Unicode code points rather than letter pairs, causing mispronunciation or silent skips.

**Reference lists** — Bibliographies are dense with author names, abbreviated journal titles, DOIs, and page ranges. They are rarely useful when read aloud and currently pass through to the TTS unchanged.

**Intended fix (R2):** allow users to upload files directly (PDF, EPUB, DOCX, HTML) rather than pasting text. Layout-aware extraction libraries (`pymupdf`, `marker`, `ebooklib`) resolve the column, table, and equation problems at the source.

---

## Deploying Your Own

### Prerequisites

- OCI account (Free Tier works for Functions, NoSQL, and Object Storage)
- AWS account (Cognito is outside OCI Free Tier but has a generous free tier)
- On-premises server with a CUDA GPU and k3s installed
- Terraform ≥ 1.6, OCI CLI, kubectl

### Steps

1. **Provision cloud infrastructure**
   ```bash
   cp terraform/terraform.tfvars.example terraform/terraform.tfvars
   # Fill in your OCI and AWS credentials
   terraform -chdir=terraform init && terraform -chdir=terraform apply
   ```

2. **Configure the OCI Function**
   ```bash
   cp fn/.env.example .env   # or set TF_VAR_* in CI
   # Deploy via Gitea Actions or manually:
   fn/deploy.sh
   ```

3. **Configure the worker**
   - Copy `worker/k8s/configmap.yaml`, fill in `<YOUR_*>` placeholders
   - Copy `worker/k8s/secret.yaml.example` → `secret.yaml`, add credentials
   - Apply: `kubectl apply -f worker/k8s/`

4. **Start a Qwen3-TTS-Base server**
   See the [faster-qwen3-tts](https://github.com/andimarafioti/faster-qwen3-tts) project.
   The worker expects an OpenAI-compatible `/v1/audio/speech` endpoint.

5. **Deploy the SPA**
   ```bash
   # Edit spa/app.js CONFIG with your API Gateway URL and Cognito client ID
   oci os object bulk-upload -bn <your-web-bucket> --src-dir spa/ --overwrite
   ```

---

## Security Posture

| Control | Implementation |
|---------|---------------|
| Authentication | AWS Cognito JWT, RS256, verified on every request |
| Transport | HTTPS enforced at API Gateway; OCI Object Storage TLS |
| Input validation | Job text limited to 100,000 chars; IDs validated against `^[a-zA-Z0-9\-]{8,64}$` |
| NoSQL injection | Input validated before string interpolation into NoSQL queries |
| Secrets | Never in source; injected via k8s Secrets and OCI Vault |
| Container | Worker runs as UID 1000 (non-root), capabilities dropped, seccomp RuntimeDefault |
| SAST | Bandit (Python), Checkov (Terraform + k8s + Dockerfile) on every commit |
| Dependency audit | pip-audit on every commit |
| Secrets scanning | TruffleHog git-history scan on every commit |
| Pen test | OWASP ZAP baseline scan: 66 checks, 0 findings |

---

## License

MIT — see [LICENSE](LICENSE).
