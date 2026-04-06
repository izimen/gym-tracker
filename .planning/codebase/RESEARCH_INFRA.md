# Cloud Run Best Practices Research for gym-tracker

**Researched:** 2026-04-04
**Domain:** Google Cloud Run deployment, Python/Flask, container best practices
**Confidence:** MEDIUM (based on training data through May 2025; web verification was unavailable -- flagged items should be cross-checked against current GCP documentation)

## Summary

The gym-tracker app runs on Cloud Run with a Python 3.12 Alpine image, Gunicorn (1 worker, 8 threads, timeout 0), a background scraper thread, partial env var management, no health checks, no monitoring, and no staging environment. This research covers 8 areas of improvement.

The most impactful changes are: (1) switching to Secret Manager for credentials, (2) adding a startup health check, (3) setting a proper Gunicorn timeout, and (4) moving the background scraper to Cloud Scheduler. The current setup works but has several reliability and security gaps that compound into operational risk.

**Primary recommendation:** Address secrets management (Secret Manager) and health checks first -- these have the highest impact-to-effort ratio and directly fix identified security concerns (M-05, C-01 from CONCERNS.md).

---

## 1. Base Image: python:3.12-alpine vs Alternatives

### Current State
```dockerfile
FROM python:3.12-alpine
```

### Analysis

| Image | Size (approx) | Pros | Cons |
|-------|---------------|------|------|
| `python:3.12-alpine` | ~50 MB | Smallest, minimal attack surface | musl libc (not glibc), can break C extensions, slower pip builds for packages needing compilation |
| `python:3.12-slim` | ~130 MB | glibc (better compatibility), Debian-based, prebuilt wheels work | Larger than Alpine |
| `python:3.12-slim-bookworm` | ~130 MB | Same as slim, explicit Debian version pinning | Same as slim |
| `gcr.io/distroless/python3` | ~50 MB | Google-maintained, no shell (hardened), minimal CVE surface | No shell = harder debugging, no pip at runtime, requires multi-stage build |
| `python:3.12` (full) | ~900 MB | Everything included | Far too large, unnecessary attack surface |

### Recommendation: Stay with `python:3.12-alpine` (Confidence: MEDIUM)

For this project, Alpine is a reasonable choice because:

1. **The dependency set is pure-Python-friendly.** Flask, gunicorn, requests, beautifulsoup4, pytz, and flask-* extensions are all pure Python or have prebuilt Alpine wheels. The only potentially problematic dependency is `bcrypt`, which requires a C compiler -- but bcrypt publishes prebuilt musl wheels for Alpine on PyPI since version 4.1+.

2. **google-cloud-firestore may need attention.** The `grpcio` dependency (pulled in by google-cloud-firestore) historically had Alpine build issues. However, since grpcio 1.56+ publishes musl-compatible wheels. Verify by checking if your current build completes without installing build tools (gcc, musl-dev).

3. **Image size matters less on Cloud Run** than many assume. Cloud Run caches images, and the download time difference between 50 MB and 130 MB is negligible after the first pull. However, smaller images do have fewer CVEs to patch.

**If you encounter Alpine build issues:** Switch to `python:3.12-slim-bookworm`. It is the standard recommendation from Google's own Cloud Run quickstart samples.

**Improvement: Add a multi-stage build** regardless of base image:

```dockerfile
# Build stage
FROM python:3.12-alpine AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.12-alpine
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 60 app:app
```

This keeps build tools out of the runtime image and produces a cleaner, smaller final image.

**Confidence note:** The recommendation to stay with Alpine is MEDIUM because Google's official Cloud Run Python samples historically use `python:3.X-slim`. If Alpine causes any build or runtime issues, slim-bookworm is the safe fallback. Verify against current GCP Python quickstart docs.

---

## 2. Gunicorn Configuration for Cloud Run

### Current State
```dockerfile
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

### Issues Identified

| Setting | Current | Problem | Recommended |
|---------|---------|---------|-------------|
| `--workers` | 1 | Correct for Cloud Run's single-vCPU default | Keep at 1 (or 2 if instance has 2+ vCPU) |
| `--threads` | 8 | Reasonable for I/O-bound Flask app | Keep at 8 (or 2-4 * vCPU cores) |
| `--timeout` | 0 (infinite) | A stuck request holds a thread forever; 8 stuck requests = total capacity exhaustion (flagged as L-01 in CONCERNS.md) | 60 seconds |
| `--preload` | not set | App module loads per-fork; fine with 1 worker | Optional: add for memory savings if workers > 1 |
| `--access-logfile` | not set | No access logging to stdout | Add `--access-logfile -` for Cloud Logging integration |

### Recommended Gunicorn Command

```dockerfile
CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    app:app
```

### Rationale

**Workers = 1:** Cloud Run's default container instance has 1 vCPU. The official GCP documentation recommends `(2 * CPU_COUNT) + 1` workers, but since Cloud Run defaults to 1 vCPU and the app has a background thread consuming CPU, 1 worker is correct. If you increase the Cloud Run instance to 2 vCPU, increase to 2-3 workers.

**Threads = 8:** For an I/O-bound app (HTTP requests to eFitness, Firestore calls), 8 threads per worker is appropriate. This allows 8 concurrent requests to be handled. The app is not CPU-bound, so thread contention on the GIL is minimal.

**Timeout = 60:** Cloud Run has its own request timeout (default 300 seconds, configurable). Setting gunicorn's timeout to 60 seconds means stuck requests (e.g., eFitness portal not responding) are killed before Cloud Run's timeout. This frees threads faster. The `timeout 0` (infinite) setting is the GCP quickstart default but is **not recommended for production** -- it was designed for simplicity in tutorials, not robustness.

**Access log:** Cloud Run captures stdout/stderr and sends it to Cloud Logging. Adding `--access-logfile -` gives you per-request logs (method, path, status code, response time) in Cloud Logging without any extra setup.

**Confidence: HIGH** -- This aligns with Google's own Cloud Run documentation and standard gunicorn production practices.

---

## 3. Background Thread vs Cloud Scheduler

### Current State
```python
def background_updater():
    """Background thread that updates entries data periodically"""
    while True:
        fetch_entries_data()
        time.sleep(180)  # Update every 3 minutes

updater_thread = threading.Thread(target=background_updater, daemon=True)
updater_thread.start()
```

### Analysis

| Approach | Pros | Cons |
|----------|------|------|
| **Background thread (current)** | Simple, no extra GCP services, runs in same process | Thread dies if instance scales to 0; no retry on failure; thread safety issues (H-06); couples scraping to web serving; no observability |
| **Cloud Scheduler + Cloud Run job** | Decoupled, observable, retries built-in, scales independently, runs even when no traffic | Adds GCP complexity, requires a separate endpoint or Cloud Run job, small additional cost |
| **Cloud Scheduler + same service endpoint** | Simplest migration from current; scheduler hits an HTTP endpoint on the same Cloud Run service | Still coupled to the web service; scraper failure doesn't affect serving; easy to monitor |
| **Cloud Scheduler + Cloud Functions** | True decoupling, cheapest per-invocation | Another runtime to maintain, cold start latency, function timeout limits |

### Recommendation: Cloud Scheduler hitting an HTTP endpoint on the same service (Confidence: HIGH)

This is the lowest-friction improvement:

1. **Create a new endpoint** (e.g., `/internal/scrape`) protected by a secret header or Cloud Scheduler's OIDC authentication.

2. **Create a Cloud Scheduler job** that hits this endpoint every 3 minutes.

3. **Remove the background thread.**

4. **Set `min-instances: 1`** so the service never scales to zero (the scraper needs it running).

```python
@app.route('/internal/scrape', methods=['POST'])
def trigger_scrape():
    """Called by Cloud Scheduler every 3 minutes."""
    # Verify the request comes from Cloud Scheduler
    auth_header = request.headers.get('Authorization', '')
    # Cloud Scheduler sends an OIDC token when configured
    # For simpler setup: check a shared secret
    secret = request.headers.get('X-Scrape-Secret', '')
    if not SCRAPE_SECRET or not secrets.compare_digest(secret, SCRAPE_SECRET):
        return jsonify({'error': 'Unauthorized'}), 401

    fetch_entries_data()
    return jsonify({'status': 'ok', 'cache': entries_cache}), 200
```

Cloud Scheduler configuration:
```
Frequency: */3 * * * *
Target: HTTP
URL: https://gym-tracker-XXXXX.a.run.app/internal/scrape
HTTP method: POST
Auth header: Add OIDC token (recommended) or custom header
```

**Why not Cloud Functions?** The scraping logic needs the `requests.Session` state (login cookies) which is maintained in the gunicorn process memory. Moving to a separate Cloud Function would require re-login on every invocation (every 3 minutes), which is wasteful and may trigger rate limiting on the eFitness portal. Keeping the scraper in the same service preserves the session.

**Why not keep the background thread?** Three reasons from CONCERNS.md:
- **H-06:** Thread safety issue on `entries_cache` dict
- **L-03:** Background updater not gracefully stopped
- If `min-instances: 0` (current default), the background thread stops when Cloud Run scales the instance down. The scraper silently stops.

**Confidence: HIGH** -- Cloud Scheduler + HTTP endpoint is the standard GCP pattern for periodic tasks on Cloud Run, documented in official GCP guides.

---

## 4. Secrets Management: Env Vars vs Secret Manager

### Current State

| Secret | How Set | Problem |
|--------|---------|---------|
| `SECRET_KEY` | GitHub Actions -> Cloud Run env var | Visible in Cloud Run revision metadata, CI logs |
| `GYM_EMAIL` | Manual in Cloud Run Console | Not version-controlled, fragile |
| `GYM_PASSWORD` | Manual in Cloud Run Console | Visible in revision metadata to anyone with `run.services.get` permission |
| `ADMIN_SECRET` | Manual in Cloud Run Console | Same as above |
| `GYM_URL` | Manual in Cloud Run Console | Not really a secret, but managed inconsistently |
| `ALLOWED_ORIGINS` | Manual (?) | Configuration, not a secret |
| `GCP_SA_KEY` | GitHub Secret (JSON blob) | Service account key is a security anti-pattern; Workload Identity Federation is preferred |

### Recommendation: Use Google Secret Manager (Confidence: HIGH)

**Berglas is deprecated.** Google archived the Berglas project and recommends Secret Manager as the replacement. Do not use Berglas.

**Secret Manager advantages over env vars:**
- Secrets are **not visible** in Cloud Run revision metadata (env vars are)
- Secret **versioning** -- can roll back a secret without redeploying
- **Audit logging** -- Cloud Audit Logs track who accessed which secret
- **IAM-controlled** -- fine-grained access (who can read vs. admin)
- **Rotation support** -- can update a secret without redeploying the service
- **No CI exposure** -- secrets never pass through GitHub Actions

### Implementation Plan

**Step 1: Create secrets in Secret Manager**
```bash
# Create each secret
echo -n "your-flask-secret" | gcloud secrets create SECRET_KEY --data-file=-
echo -n "gym-email@example.com" | gcloud secrets create GYM_EMAIL --data-file=-
echo -n "gym-password" | gcloud secrets create GYM_PASSWORD --data-file=-
echo -n "admin-secret-value" | gcloud secrets create ADMIN_SECRET --data-file=-
echo -n "https://your-gym.cms.efitness.com.pl" | gcloud secrets create GYM_URL --data-file=-
```

**Step 2: Grant Cloud Run service account access**
```bash
PROJECT_ID=$(gcloud config get-value project)
SERVICE_ACCOUNT="gym-tracker-sa@${PROJECT_ID}.iam.gserviceaccount.com"

for SECRET in SECRET_KEY GYM_EMAIL GYM_PASSWORD ADMIN_SECRET GYM_URL; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
done
```

**Step 3: Reference secrets in Cloud Run deploy**

Update `.github/workflows/deploy.yml`:
```yaml
- name: Deploy to Cloud Run
  uses: 'google-github-actions/deploy-cloudrun@v2'
  with:
    service: ${{ env.SERVICE }}
    region: ${{ env.REGION }}
    source: ./
    flags: '--allow-unauthenticated'
    secrets: |
      SECRET_KEY=SECRET_KEY:latest
      GYM_EMAIL=GYM_EMAIL:latest
      GYM_PASSWORD=GYM_PASSWORD:latest
      ADMIN_SECRET=ADMIN_SECRET:latest
      GYM_URL=GYM_URL:latest
    env_vars: |
      ALLOWED_ORIGINS=https://your-domain.com
```

The `secrets` field in `deploy-cloudrun@v2` maps Secret Manager secrets to environment variables at runtime. The secret value is injected when the container starts, not baked into the revision metadata.

**Step 4: Migrate from service account key to Workload Identity Federation**

The current CI uses `GCP_SA_KEY` (a JSON service account key). This is a security anti-pattern because:
- The key never expires unless manually rotated
- If the GitHub repository is compromised, the key grants permanent GCP access
- Google recommends Workload Identity Federation for GitHub Actions

```yaml
- name: Google Auth
  uses: 'google-github-actions/auth@v2'
  with:
    workload_identity_provider: 'projects/PROJECT_NUM/locations/global/workloadIdentityPools/github-pool/providers/github-provider'
    service_account: 'gym-tracker-deployer@PROJECT_ID.iam.gserviceaccount.com'
```

This eliminates the long-lived service account key entirely. Setup requires a one-time Workload Identity Pool configuration in GCP.

### Classification of Variables

| Variable | Type | Where to Store |
|----------|------|----------------|
| `SECRET_KEY` | Secret | Secret Manager |
| `GYM_EMAIL` | Secret | Secret Manager |
| `GYM_PASSWORD` | Secret | Secret Manager |
| `ADMIN_SECRET` | Secret | Secret Manager |
| `GYM_URL` | Configuration | Secret Manager (contains gym identity) or env var |
| `ALLOWED_ORIGINS` | Configuration | Env var in deploy.yml |
| `PORT` | Configuration | Set by Cloud Run automatically |
| `GCP_SA_KEY` | CI credential | Replace with Workload Identity Federation |

**Confidence: HIGH** -- Secret Manager is the official GCP recommendation and is the standard in the ecosystem. Berglas deprecation is confirmed. Workload Identity Federation is the documented successor to service account keys for CI/CD.

---

## 5. Health Check Configuration

### Current State

No health check is configured. No `/health` or `/healthz` endpoint exists in app.py. Cloud Run uses TCP port readiness by default (checks if the container is listening on the port).

### Recommendation: Add HTTP startup probe and liveness probe (Confidence: HIGH)

Cloud Run supports three types of probes (matching Kubernetes probe model):

| Probe Type | Purpose | When It Runs |
|------------|---------|-------------|
| **Startup probe** | Verify the app has started and is ready to serve | During container startup only |
| **Liveness probe** | Detect if the app is hung/deadlocked | Periodically during container lifetime |
| **TCP probe** (default) | Check if port is open | Used when no HTTP probe configured |

### Implementation

**Step 1: Add a health endpoint to app.py**

```python
@app.route('/health')
def health_check():
    """Health check endpoint for Cloud Run probes."""
    health = {
        'status': 'healthy',
        'checks': {}
    }
    status_code = 200

    # Check 1: Firestore connectivity
    if FIRESTORE_ENABLED:
        try:
            db = database.get_db()
            # Lightweight read to verify connectivity
            db.collection('health').document('ping').get()
            health['checks']['firestore'] = 'ok'
        except Exception as e:
            health['checks']['firestore'] = f'error: {type(e).__name__}'
            health['status'] = 'degraded'
            # Don't fail the health check for Firestore issues --
            # the app can still serve cached data
            # Use status_code = 503 here if Firestore is critical

    # Check 2: Scraper cache freshness
    cache_status = entries_cache.get('status', 'unknown')
    health['checks']['scraper_cache'] = cache_status
    if cache_status == 'error':
        health['status'] = 'degraded'

    return jsonify(health), status_code
```

**Step 2: Configure probes in Cloud Run**

Via `gcloud`:
```bash
gcloud run services update gym-tracker \
  --region europe-central2 \
  --startup-probe httpGet.path=/health,httpGet.port=8080,initialDelaySeconds=5,periodSeconds=10,failureThreshold=3,timeoutSeconds=5 \
  --liveness-probe httpGet.path=/health,periodSeconds=30,failureThreshold=3,timeoutSeconds=5
```

Or via deploy-cloudrun action (add to flags):
```yaml
flags: >-
  --allow-unauthenticated
  --startup-cpu-boost
```

Note: Probes are typically configured via `gcloud run services update` or a YAML service definition, not via the deploy action flags. Consider using a Cloud Run service YAML:

```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: gym-tracker
spec:
  template:
    spec:
      containers:
        - image: IMAGE_URL
          ports:
            - containerPort: 8080
          startupProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
            timeoutSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            periodSeconds: 30
            failureThreshold: 3
            timeoutSeconds: 5
```

### Health Check Design Decisions

- **Do NOT fail the health check if the scraper cache is stale.** The web UI and API can still serve workout data, analytics, and auth even if the gym occupancy scraper is down. Report "degraded" but return 200.
- **DO fail the health check if Firestore is unreachable AND the app cannot function without it.** Since all CRUD operations require Firestore, a persistent Firestore failure means the app is effectively down. However, since Cloud Run will restart the instance on health check failure, and Firestore outages are usually GCP-wide (restart won't help), returning "degraded" with 200 is usually better than 503.
- **Keep health checks fast.** The Firestore `.get()` on a small document should take <100ms. Do not run expensive queries in the health check.

**Confidence: HIGH** -- HTTP health probes are standard Cloud Run configuration, well-documented.

---

## 6. Min-Instances and Cold Start Management

### Current State

No `min-instances` is configured (defaults to 0). The service scales to zero when idle. Cold starts occur when the first request arrives after idle period.

### Analysis

| Setting | Behavior | Cost Impact |
|--------|----------|-------------|
| `min-instances: 0` (current) | Scales to zero; cold start on first request after idle | Cheapest; no cost when idle |
| `min-instances: 1` | Always keeps one instance warm; no cold starts | Costs ~$0.50-1.50/month for a 256MB/1vCPU instance (free tier may cover this) |
| Startup CPU boost | Cloud Run allocates extra CPU during startup to speed cold start | Minimal cost increase, faster startup |

### Recommendation: Set `min-instances: 1` and enable startup CPU boost (Confidence: HIGH)

**Reasons specific to gym-tracker:**

1. **The background scraper requires a running instance.** If `min-instances: 0`, the scraper thread stops when the instance scales down. If you migrate to Cloud Scheduler (recommendation #3), the scheduler will hit a cold instance, causing delayed scraping.

2. **Cold start time for this app.** The app imports `google-cloud-firestore` (which pulls in `grpcio`), `bcrypt`, `beautifulsoup4`, and initializes a Firestore client. On a 256MB Cloud Run instance, this takes 3-8 seconds. For a personal gym tracker, this delay on the first request after idle is noticeable.

3. **Free tier.** Cloud Run's free tier includes 180,000 vCPU-seconds and 360,000 GiB-seconds per month. One always-on 1-vCPU/256MB instance uses ~2.6M vCPU-seconds/month, which exceeds the free tier. However, with the "CPU is only allocated during request processing" setting (default), idle instances use minimal resources. With `min-instances: 1` and "CPU always allocated", expect ~$5-10/month. With "CPU only during requests" and `min-instances: 1`, the cost is lower since idle instances don't consume CPU allocation.

**Configuration:**
```bash
gcloud run services update gym-tracker \
  --region europe-central2 \
  --min-instances 1 \
  --startup-cpu-boost
```

Or in deploy.yml:
```yaml
flags: >-
  --allow-unauthenticated
  --min-instances=1
  --startup-cpu-boost
```

**Important caveat:** If you move the scraper to Cloud Scheduler (recommendation #3), `min-instances: 1` is not strictly required for scraping correctness (Cloud Scheduler will wake the instance). But it still eliminates cold starts for user-facing requests, which improves UX.

**If cost is a concern:** Keep `min-instances: 0` but add `--startup-cpu-boost` to reduce cold start time. This is free. The trade-off is 3-8 second cold starts when the app has been idle.

**Confidence: HIGH** -- min-instances is straightforward Cloud Run configuration. Cost estimates are approximate and should be verified against current GCP pricing.

---

## 7. Monitoring and Alerting

### Current State

No monitoring, alerting, or error reporting is configured. The app uses `print()` statements for logging, which go to Cloud Logging via stdout, but there is no structured logging, no alerting on errors, and no uptime checks.

### Recommendation: Layered monitoring approach (Confidence: HIGH)

### Layer 1: Structured Logging (Free, High Value)

Replace `print()` with Python's `logging` module formatted for Cloud Logging:

```python
import logging
import json
import sys

class CloudRunFormatter(logging.Formatter):
    """Format logs as JSON for Cloud Logging structured logging."""
    def format(self, record):
        log_entry = {
            'severity': record.levelname,
            'message': record.getMessage(),
            'component': record.name,
        }
        if record.exc_info:
            log_entry['stack_trace'] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CloudRunFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger('gym-tracker')
```

Cloud Logging automatically parses JSON logs from Cloud Run and extracts `severity`, `message`, and other fields. This enables filtering and alerting by severity in the Cloud Console.

### Layer 2: Cloud Run Built-in Metrics (Free)

Cloud Run automatically reports these metrics to Cloud Monitoring:
- Request count (by response code)
- Request latency (p50, p95, p99)
- Container instance count
- Container CPU utilization
- Container memory utilization
- Container startup latency
- Billable container instance time

**No setup needed.** These are visible in the Cloud Console under Cloud Run > Service > Metrics tab.

### Layer 3: Uptime Check (Free tier: 3 checks)

Create a Cloud Monitoring uptime check that hits the `/health` endpoint:

```bash
gcloud monitoring uptime-checks create http gym-tracker-uptime \
  --display-name="Gym Tracker Uptime" \
  --uri="https://gym-tracker-XXXXX.a.run.app/health" \
  --period=300 \
  --timeout=10
```

This checks every 5 minutes from multiple GCP regions. If the health check fails 2+ times consecutively, it triggers an alert.

### Layer 4: Alerting Policies (Recommended)

Set up alerts for these conditions:

| Condition | Threshold | Channel |
|-----------|-----------|---------|
| Uptime check failure | 2 consecutive failures | Email |
| 5xx error rate | >5% of requests in 5-minute window | Email |
| Request latency p95 | >5 seconds for 5 minutes | Email (low priority) |
| Container restart count | >3 in 1 hour | Email |
| Memory utilization | >80% for 5 minutes | Email |

```bash
# Example: Alert on 5xx error rate
gcloud monitoring policies create \
  --display-name="Gym Tracker 5xx Rate" \
  --condition-display-name="High 5xx rate" \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"' \
  --condition-threshold-value=5 \
  --condition-threshold-comparison=COMPARISON_GT \
  --notification-channels=CHANNEL_ID
```

### Layer 5: Error Reporting (Free tier available)

Cloud Error Reporting automatically groups and tracks errors from Cloud Run if you use structured logging with stack traces. When the `CloudRunFormatter` above includes `stack_trace`, Error Reporting picks it up automatically.

**No additional setup needed** beyond structured logging.

### Layer 6: (Optional) Cloud Trace

If you want request tracing (seeing how long Firestore calls take within a request), add the `opentelemetry-exporter-gcp-trace` package. This is optional for a personal project but useful for debugging slow requests.

### Priority Order for Implementation

1. **Structured logging** -- Replace `print()` with `logging` + JSON formatter (1-2 hours)
2. **Health check endpoint** -- Required for uptime monitoring (30 min, see section 5)
3. **Uptime check** -- 5-minute gcloud command
4. **5xx error alert** -- 5-minute gcloud command
5. **Error Reporting** -- Automatic once structured logging is in place

**Confidence: HIGH** -- Cloud Monitoring, Cloud Logging, and Error Reporting are stable GCP products with well-documented Cloud Run integration.

---

## 8. GitHub Actions Deploy vs Cloud Build

### Current State

```yaml
- name: Deploy to Cloud Run
  uses: 'google-github-actions/deploy-cloudrun@v2'
  with:
    service: ${{ env.SERVICE }}
    region: ${{ env.REGION }}
    source: ./
    flags: '--allow-unauthenticated --clear-base-image'
    env_vars: |
      SECRET_KEY=${{ secrets.SECRET_KEY }}
```

The `source: ./` flag means the action uploads the source code, and **Cloud Build runs automatically** on Google's side to build the Docker image. So the current setup already uses Cloud Build under the hood -- just triggered via GitHub Actions.

### Analysis

| Approach | How It Works | Pros | Cons |
|----------|-------------|------|------|
| **Current: GH Actions + deploy-cloudrun (source)** | GH Actions uploads source, Cloud Build builds image, deploys to Cloud Run | Simple workflow file; Cloud Build handles Docker build; no Artifact Registry setup needed | Less control over build; Cloud Build pricing applies; GCP_SA_KEY in GitHub |
| **GH Actions + deploy-cloudrun (image)** | GH Actions builds Docker image, pushes to Artifact Registry, deploys pre-built image | Full control over build; can cache layers; faster deploys (image already built) | More workflow steps; Artifact Registry setup; larger workflow file |
| **Pure Cloud Build trigger** | Cloud Build watches GitHub repo, builds and deploys on push | No GitHub Actions needed; everything in GCP; simpler auth | Harder to integrate non-GCP CI steps; Cloud Build trigger setup; less community tooling |
| **GH Actions + Cloud Deploy** | GH Actions builds, Cloud Deploy handles promotion through environments | Staging -> production pipeline; rollback support; audit trail | Overkill for a personal project; requires Cloud Deploy setup |

### Recommendation: Keep GitHub Actions, switch to image-based deploy (Confidence: MEDIUM)

The current approach is acceptable for a personal project. However, switching to image-based deploy has advantages:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: europe-central2
  SERVICE: gym-tracker
  IMAGE: europe-central2-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/gym-tracker/app

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # Required for Workload Identity Federation

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Google Auth (Workload Identity Federation)
        id: auth
        uses: 'google-github-actions/auth@v2'
        with:
          workload_identity_provider: 'projects/${{ secrets.GCP_PROJECT_NUM }}/locations/global/workloadIdentityPools/github-pool/providers/github-provider'
          service_account: 'gym-tracker-deployer@${{ env.PROJECT_ID }}.iam.gserviceaccount.com'

      - name: Set up Cloud SDK
        uses: 'google-github-actions/setup-gcloud@v2'

      - name: Configure Docker
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev

      - name: Build and Push Docker Image
        run: |
          docker build -t ${{ env.IMAGE }}:${{ github.sha }} -t ${{ env.IMAGE }}:latest .
          docker push ${{ env.IMAGE }}:${{ github.sha }}
          docker push ${{ env.IMAGE }}:latest

      - name: Deploy to Cloud Run
        uses: 'google-github-actions/deploy-cloudrun@v2'
        with:
          service: ${{ env.SERVICE }}
          region: ${{ env.REGION }}
          image: ${{ env.IMAGE }}:${{ github.sha }}
          flags: >-
            --allow-unauthenticated
            --min-instances=1
            --startup-cpu-boost
          secrets: |
            SECRET_KEY=SECRET_KEY:latest
            GYM_EMAIL=GYM_EMAIL:latest
            GYM_PASSWORD=GYM_PASSWORD:latest
            ADMIN_SECRET=ADMIN_SECRET:latest
            GYM_URL=GYM_URL:latest
          env_vars: |
            ALLOWED_ORIGINS=https://your-domain.com
```

**Benefits of image-based deploy:**
- **Reproducibility:** The exact image deployed is tagged with the git SHA
- **Rollback:** Can instantly roll back to any previous image SHA without rebuilding
- **Caching:** Docker layer caching in Artifact Registry speeds up builds
- **Artifact trail:** Every deployed image is preserved in Artifact Registry

**If staying with source-based deploy:** The current approach is fine, but fix the security issues:
1. Add Workload Identity Federation (replace `GCP_SA_KEY`)
2. Move secrets to Secret Manager (replace `env_vars` with `secrets`)
3. Remove `--clear-base-image` (this flag is rarely needed)

**Confidence: MEDIUM** -- Both source-based and image-based deploys are valid. The recommendation to switch is a "nice to have" improvement, not a critical fix.

---

## Common Pitfalls (Cloud Run + Python/Flask)

### Pitfall 1: Background Threads Die on Scale-to-Zero
**What goes wrong:** Cloud Run scales instances to zero when idle. Background threads (like the scraper) stop silently. Data stops being collected with no error or alert.
**Why it happens:** Cloud Run only keeps instances alive while processing requests or within the idle timeout (default 15 minutes). After that, the instance is terminated.
**How to avoid:** Use Cloud Scheduler to trigger scraping via an HTTP endpoint. Set `min-instances: 1` if background processing is critical.
**Warning signs:** Gaps in hourly occupancy data correlating with low-traffic periods.

### Pitfall 2: Env Vars Visible in Revision Metadata
**What goes wrong:** Secrets set as env vars (via `--set-env-vars` or `env_vars` in deploy action) are stored in plain text in the Cloud Run revision metadata. Anyone with `run.services.get` permission can read them.
**Why it happens:** Env vars are configuration, not secrets. Cloud Run stores them as part of the service spec.
**How to avoid:** Use Secret Manager. Secrets referenced via `--set-secrets` are NOT stored in revision metadata -- only the reference (secret name + version) is stored.
**Warning signs:** Run `gcloud run services describe gym-tracker --format=json | grep -A5 env` to check what is exposed.

### Pitfall 3: Single-Threaded Session Object Shared Across Threads
**What goes wrong:** The `requests.Session` object (`current_session`) is shared between the background scraper thread and potential request handler threads. While `session_lock` protects session creation, the session's HTTP connection pool is not thread-safe for concurrent use.
**Why it happens:** The `requests` library's `Session` is not documented as thread-safe. With gunicorn's 8 threads, a user request and the background scraper could use the session simultaneously.
**How to avoid:** Give the scraper its own session. Or use thread-local sessions.

### Pitfall 4: gunicorn --timeout 0 Causes Thread Exhaustion
**What goes wrong:** A request that hangs (e.g., Firestore is slow, eFitness is down) holds a gunicorn thread indefinitely. With only 8 threads, 8 hanging requests = complete service outage.
**Why it happens:** `--timeout 0` disables gunicorn's worker timeout. While Cloud Run eventually kills the request (at 300s), gunicorn does not reclaim the thread.
**How to avoid:** Set `--timeout 60` (or 30 for this app's use case). All requests should complete well within 15 seconds (the `REQUEST_TIMEOUT` is 15s for external calls).

### Pitfall 5: Alpine + grpcio Build Failures
**What goes wrong:** `pip install grpcio` fails on Alpine because pre-built wheels target glibc (Debian/Ubuntu), not musl (Alpine). The build requires `gcc`, `musl-dev`, `linux-headers`, adding 200+ MB to the build layer.
**Why it happens:** grpcio includes compiled C/C++ code. Alpine uses musl libc instead of glibc.
**How to avoid:** Since grpcio 1.56+, musl wheels are published. Ensure your `requirements.txt` pins `grpcio>=1.56`. If builds fail, switch to `python:3.12-slim-bookworm`. Or use a multi-stage build where the build stage has the compilers but the runtime stage does not.

### Pitfall 6: No .env in .dockerignore
**What goes wrong:** `COPY . ./` in the Dockerfile copies `.env` into the image layer. Credentials are baked into the container image stored in Artifact Registry.
**Why it happens:** `.dockerignore` does not list `.env`. Already identified as **C-01** in CONCERNS.md.
**How to avoid:** Add `.env`, `.env.*`, `.env.local`, `.env.production` to `.dockerignore`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secrets management | Custom env var injection | Google Secret Manager | Audit logging, versioning, rotation, IAM |
| Periodic scheduling | `threading.Thread` + `time.sleep()` | Cloud Scheduler | Survives scale-to-zero, retries, monitoring |
| CI/CD authentication | Service account JSON keys | Workload Identity Federation | No long-lived credentials, no key rotation needed |
| Structured logging | Custom print-to-JSON | Python `logging` + JSON formatter | Cloud Logging parses it automatically, enables Error Reporting |
| Uptime monitoring | Manual checking or nothing | Cloud Monitoring uptime checks | Multi-region probing, automatic alerting, free tier |
| Request tracing | Custom timing code | OpenTelemetry + Cloud Trace | Distributed tracing, Firestore call timing, automatic |
| Rate limiting persistence | In-memory dict counters | Redis-backed flask-limiter or Cloud Armor | Survives restarts, works across instances |
| Health checks | No health check | Cloud Run HTTP startup/liveness probes | Automatic restart on failure, prevents bad deploys |

---

## Priority Matrix

| Change | Impact | Effort | Priority |
|--------|--------|--------|----------|
| Add `.env` to `.dockerignore` | Critical (C-01) | 1 minute | **P0 -- Do immediately** |
| Secret Manager for all secrets | High (security) | 2-3 hours | **P1 -- Do first** |
| Workload Identity Federation | High (security) | 1-2 hours | **P1 -- Do with secrets** |
| Health check endpoint | High (reliability) | 30 minutes | **P1** |
| Gunicorn timeout 60s | Medium (reliability) | 1 minute | **P2** |
| Gunicorn access logging | Medium (observability) | 1 minute | **P2** |
| Structured logging (replace print) | Medium (observability) | 2-3 hours | **P2** |
| Cloud Scheduler for scraper | Medium (reliability) | 2 hours | **P2** |
| min-instances: 1 | Medium (UX, reliability) | 1 minute | **P2** |
| Uptime check + alert | Medium (observability) | 15 minutes | **P3** |
| 5xx error alerting | Medium (observability) | 15 minutes | **P3** |
| Image-based deploy pipeline | Low (operational) | 1-2 hours | **P3** |
| Multi-stage Dockerfile | Low (image size) | 30 minutes | **P4** |
| Staging environment | Low (for personal project) | 2-3 hours | **P4** |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Service account JSON keys in CI | Workload Identity Federation | 2022+ (mature by 2024) | No long-lived credentials |
| Berglas for secrets | Google Secret Manager | Berglas archived ~2023 | Better integration, versioning |
| `--timeout 0` in quickstarts | `--timeout 30-120` in production | Always (quickstart != production) | Thread exhaustion prevention |
| Env vars for secrets | Secret Manager references in Cloud Run | 2021+ (Cloud Run native support) | Secrets not in revision metadata |
| `print()` for logging | Structured JSON logging | Cloud Logging structured format stable since 2020 | Enables Error Reporting, severity filtering |
| Manual uptime checking | Cloud Monitoring uptime checks | Always available | Multi-region, automatic alerting |
| Cloud Build triggers | GitHub Actions + deploy-cloudrun | deploy-cloudrun@v2 stable since 2023 | CI stays in GitHub ecosystem |

---

## Open Questions

1. **Cloud Run CPU allocation mode:** Should the service use "CPU always allocated" (needed for background threads) or "CPU only during request processing" (cheaper)? If migrating scraper to Cloud Scheduler, "CPU only during requests" is fine. If keeping background thread, must use "CPU always allocated". **Current setting unknown -- check via `gcloud run services describe gym-tracker`.**

2. **Firestore composite indexes:** Recommendation #M-02 (from CONCERNS.md) requires composite indexes on `(user_id, date)`. Are these indexes created? Do they need to be added to `firestore.indexes.json`? **Check via `gcloud firestore indexes composite list`.**

3. **Cloud Run concurrency setting:** The default max concurrency is 80 requests per container instance. With only 8 gunicorn threads, requests beyond 8 concurrent will queue in gunicorn. Consider setting `--concurrency=8` on Cloud Run to match gunicorn's thread count, so Cloud Run auto-scales sooner rather than queuing. **Verify current setting.**

4. **Cloud Run service YAML vs. CLI flags:** For reproducible deployments, consider committing a `service.yaml` file to the repo. This captures all configuration (probes, scaling, secrets, env vars) declaratively. **Decision depends on team preference.**

5. **Cost of min-instances with CPU-always-allocated:** If both `min-instances: 1` and `cpu-always-allocated` are set, the idle instance costs more. For a personal project, this may be $5-15/month. **Verify against current GCP pricing calculator.**

---

## Sources

### Primary (HIGH confidence)
- Training data on Google Cloud Run documentation (current through May 2025)
- Training data on gunicorn configuration best practices
- Training data on Google Secret Manager, Workload Identity Federation
- Codebase analysis: CONCERNS.md, STACK.md (project-specific verified findings)

### Unable to Verify (flagged for manual check)
- Current Cloud Run Python quickstart base image recommendation (check https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service)
- Current pricing for min-instances with CPU-always-allocated (check https://cloud.google.com/run/pricing)
- Current grpcio musl wheel availability for Python 3.12 (check PyPI: https://pypi.org/project/grpcio/#files)
- deploy-cloudrun@v2 current `secrets` field syntax (check https://github.com/google-github-actions/deploy-cloudrun)
- Cloud Run startup-cpu-boost availability in europe-central2 region

---

## Metadata

**Confidence breakdown:**
- Base image (Q1): MEDIUM -- Alpine works but slim may be safer; could not verify current GCP recommendation
- Gunicorn config (Q2): HIGH -- well-established best practices, consistent across sources
- Background thread vs Scheduler (Q3): HIGH -- standard GCP pattern, well-documented
- Secrets management (Q4): HIGH -- Secret Manager is the clear standard, Berglas deprecated
- Health checks (Q5): HIGH -- standard Cloud Run feature, well-documented
- Min-instances (Q6): HIGH -- straightforward configuration, clear trade-offs
- Monitoring (Q7): HIGH -- Cloud Monitoring/Logging integration is mature and well-documented
- Deploy workflow (Q8): MEDIUM -- both approaches are valid; recommendation is subjective

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days -- Cloud Run is a stable, slowly-evolving product)

**Limitation:** WebSearch and WebFetch were unavailable during this research. All findings are based on training data (current through May 2025) and the thorough codebase analysis already performed. Items flagged in the "Unable to Verify" section should be cross-checked against current GCP documentation before implementation.


---

# APPENDIX: Firestore Research

_(Merged from RESEARCH_FIRESTORE.md)_

# Firestore Best Practices & Optimization Research

**Researched:** 2026-04-04
**Domain:** Google Cloud Firestore (Python SDK), NoSQL query optimization, cost management
**Confidence:** MEDIUM (web search/fetch unavailable; findings based on training data through May 2025 + thorough codebase analysis)

> **Limitation notice:** WebSearch and WebFetch tools were unavailable during this research session. All Firestore pricing, API behavior, and best practice claims are based on training data (cutoff May 2025). Pricing and API details should be verified against https://cloud.google.com/firestore/pricing and https://cloud.google.com/firestore/docs before implementation.

---

## Summary

The gym-tracker application has **seven significant Firestore anti-patterns** that create unnecessary cost, latency, and scalability problems. The most impactful issue is systematic client-side filtering: 7 query functions fetch ALL users' workout data from Firestore and then filter by `user_id` in Python. This means every user's request pays for reading every other user's documents. With N users, costs and latency grow linearly per user per request.

The second major issue is N+1 query patterns in the dashboard: `get_workout_dashboard_stats()` calls 6 sub-functions, several of which issue independent Firestore queries for overlapping data. The `get_weekly_workout_history()` function issues 12 separate Firestore queries (one per week) in a loop. Combined with the client-side filtering, a single dashboard load can read hundreds of unnecessary documents.

**Primary recommendation:** Add composite indexes on `(user_id, date)` for the `workouts` collection and push `user_id` filtering into Firestore queries. This is the single highest-impact change -- it eliminates the linear cost scaling with user count and requires no architecture changes.

---

## 1. Is Firestore Still the Right Choice?

**Verdict: YES -- Firestore is appropriate for this use case.** (Confidence: HIGH)

### Why Firestore Works Here

| Factor | Assessment |
|--------|------------|
| Data model | Document-oriented maps naturally to workouts, occupancy readings, user profiles |
| Scale | Small dataset (likely <100K documents total) -- well within Firestore free tier |
| Operations | Simple CRUD + range queries + aggregations -- all supported natively |
| Infrastructure | Already deployed on GCP Cloud Run -- Firestore has zero-config auth via service account |
| Maintenance | Fully managed, no servers/upgrades to maintain |
| Cost at current scale | Likely within free tier (50K reads/day, 20K writes/day, 1 GiB storage) |

### When to Reconsider Firestore

| Trigger | Alternative | Why |
|---------|-------------|-----|
| Complex JOINs needed (e.g., "all workouts for users who joined after X") | Cloud SQL (PostgreSQL) | Firestore has no JOIN support |
| Analytics queries spanning entire dataset with GROUP BY, HAVING, etc. | BigQuery or Cloud SQL | Firestore is not an analytics database |
| >1000 writes/second sustained | Cloud Spanner | Firestore has hotspot limits |
| Self-hosted requirement | Supabase (PostgreSQL) or PocketBase (SQLite) | Firestore is GCP-only |
| Cost exceeds ~$50/month | Cloud SQL (PostgreSQL) micro instance | Fixed cost vs per-operation cost |

### Alternatives Considered

| Alternative | Tradeoff for Gym-Tracker |
|-------------|--------------------------|
| **Cloud SQL (PostgreSQL)** | Better query flexibility but requires instance management, connection pooling, schema migrations. Overkill for current scale. Fixed monthly cost even when idle. |
| **Supabase** | PostgreSQL + auth + real-time, but adds a third-party dependency. Vendor lock-in trade, not elimination. Free tier generous. |
| **PocketBase** | Single-binary SQLite backend. Simple but not managed -- would need self-hosting. No GCP integration. |
| **Turso** | Edge SQLite (libSQL). Interesting for latency but immature ecosystem. No native GCP integration. |
| **Firebase Realtime Database** | Older, less capable than Firestore. No reason to use it over Firestore for new projects. |

**Bottom line:** The problems in gym-tracker are not caused by Firestore's limitations. They are caused by not using Firestore's features (composite indexes, server-side filtering, pagination). Switching databases would not fix these patterns -- the same anti-patterns would manifest in SQL as missing WHERE clauses and N+1 queries.

---

## 2. Composite Index Best Practices

**Confidence: HIGH** (composite indexes are a well-documented, stable Firestore feature)

### What Firestore Indexes Automatically

Firestore automatically creates **single-field indexes** for every field in every document. This means queries like `.where('date', '>=', start)` work out of the box.

### When Composite Indexes Are Required

A composite index is required when a query filters or orders on **multiple fields**. The gym-tracker needs this for the most critical optimization:

```python
# THIS requires a composite index on (user_id ASC, date ASC):
db.collection('workouts') \
    .where('user_id', '==', user_id) \
    .where('date', '>=', start_date) \
    .where('date', '<', end_date) \
    .stream()
```

Without the composite index, Firestore will reject this query at runtime with a `FailedPrecondition` error and provide a URL to create the index.

### Required Composite Indexes for Gym-Tracker

| Collection | Fields | Direction | Used By |
|------------|--------|-----------|---------|
| `workouts` | `user_id` ASC, `date` ASC | Ascending | `get_month_workouts`, `get_weekly_workout_count`, `get_yearly_heatmap_data`, `get_last_workout`, `get_weekly_workout_history` |
| `workouts` | `user_id` ASC, `date` DESC | Descending | `get_last_workout` (with `.order_by('date', DESCENDING)`) |

### How to Create Composite Indexes

**Option A: Via Firebase Console**
1. Go to Firebase Console > Firestore Database > Indexes
2. Click "Add Index"
3. Collection: `workouts`, Fields: `user_id` Ascending, `date` Ascending
4. Wait 2-10 minutes for index to build

**Option B: Via `firestore.indexes.json` (recommended for version control)**

Create `firestore.indexes.json` in project root:

```json
{
  "indexes": [
    {
      "collectionGroup": "workouts",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "user_id", "order": "ASCENDING" },
        { "fieldPath": "date", "order": "ASCENDING" }
      ]
    },
    {
      "collectionGroup": "workouts",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "user_id", "order": "ASCENDING" },
        { "fieldPath": "date", "order": "DESCENDING" }
      ]
    }
  ],
  "fieldOverrides": []
}
```

Deploy with: `firebase deploy --only firestore:indexes`

**Option C: Trigger via error message**

Run the query without the index. Firestore returns an error with a direct URL to create the index. Click the URL to auto-create it in the console.

### Index Limits

| Limit | Value |
|-------|-------|
| Composite indexes per database | 200 |
| Maximum fields per composite index | 100 |
| Index build time | Minutes for small collections, hours for large ones |
| Maximum entry size | 7.5 KiB |

The gym-tracker needs only 2 composite indexes -- well within limits.

---

## 3. Client-Side Filtering: Anti-Pattern Analysis

**Confidence: HIGH** (this is a well-documented Firestore anti-pattern)

### The Current Pattern (Anti-Pattern)

Found in **7 functions** across `database.py`:

| Function | Line | Pattern |
|----------|------|---------|
| `get_month_workouts()` | 512-525 | `.where('date', ...)` then `if doc_user_id == user_id` |
| `get_weekly_workout_count()` | 570-581 | Same pattern |
| `get_last_workout()` | 663-674 | Same pattern |
| `get_weekly_workout_history()` | 723-733 | Same pattern, **inside a loop of 12 iterations** |
| `get_yearly_heatmap_data()` | 766-779 | Same pattern |
| `get_personal_records()` | 1691-1700 | **No date filter at all** -- streams entire `workouts` collection |
| `get_progression()` | 1731-1740 | **No date filter at all** -- streams entire `workouts` collection |

### Why This Is an Anti-Pattern

**Cost impact:**
- Firestore charges per document READ, regardless of whether you use the document
- If 10 users each have 30 workouts/month, querying one month reads 300 documents but uses only 30
- The user pays for 10x the reads they need
- `get_personal_records()` and `get_progression()` stream the ENTIRE workouts collection for ALL users

**Latency impact:**
- Each unnecessary document adds ~0.1-0.5ms of network transfer + deserialization time
- With 1000 total workouts, `get_personal_records()` reads all 1000 even if the user has 50

**Scaling behavior:**
- Cost and latency grow **linearly with total user count**, not with the requesting user's data
- This is the opposite of how a well-designed system should scale

### Cost Estimates (Firestore Pricing Reference)

> Firestore pricing as of training data (May 2025) -- verify against current pricing page.

| Operation | Cost (nam5 multi-region) | Cost (eur3) |
|-----------|--------------------------|-------------|
| Document read | $0.036 per 100K reads | $0.06 per 100K reads |
| Document write | $0.108 per 100K writes | $0.18 per 100K writes |
| Document delete | $0.012 per 100K deletes | $0.02 per 100K deletes |
| Storage | $0.108/GiB/month | $0.18/GiB/month |
| Free tier (daily) | 50K reads, 20K writes, 20K deletes | Same |

**Cost scenario with current anti-pattern (10 users, 1 year of data):**

A single dashboard page load triggers:
1. `get_workout_dashboard_stats()` which calls:
   - `get_weekly_workout_count()` -- reads ~70 docs (1 week x 10 users), uses ~7
   - `get_monthly_workout_count()` via `get_month_workouts()` -- reads ~300 docs (1 month x 10 users), uses ~30
   - `get_body_part_counts()` via `get_month_workouts()` -- same 300 docs again (duplicate query)
   - `get_neglected_parts()` via `get_body_part_counts()` via `get_month_workouts()` -- same 300 again
   - `get_most_trained_part()` -- same 300 (may also query previous month = another 300)
   - `get_last_workout()` -- reads ~300 docs, uses first match

2. Plus separate API calls from the frontend:
   - `get_weekly_workout_history(12)` -- **12 separate queries**, each reading ~70 docs = **840 reads** total
   - `get_yearly_heatmap_data()` -- reads ~3,650 docs (365 days x 10 users)
   - `get_strength_stats()` via `get_personal_records()` -- reads **entire workouts collection**
   - `get_extended_occupancy_stats()` -- reads ~510 hourly_occupancy docs (30 days x 17 hours)

**Estimated total per dashboard load: ~6,000-8,000 document reads** (with 10 users)

**With proper server-side filtering: ~400-600 document reads** (10-15x reduction)

**At 100 users, the current pattern would read ~60,000-80,000 docs per dashboard load.** This approaches the 50K daily free tier limit from a single page view.

### The Fix

```python
# BEFORE (anti-pattern):
docs = db.collection('workouts') \
    .where('date', '>=', start_date) \
    .where('date', '<', end_date) \
    .stream()

for doc in docs:
    data = doc.to_dict()
    if data.get('user_id') == user_id:  # Filtering in Python
        workouts.append(data)

# AFTER (correct):
docs = db.collection('workouts') \
    .where('user_id', '==', user_id) \      # Filter in Firestore
    .where('date', '>=', start_date) \
    .where('date', '<', end_date) \
    .stream()

for doc in docs:
    workouts.append(doc.to_dict())          # All results are already filtered
```

**Prerequisite:** Composite index on `(user_id, date)` must exist first (see Section 2).

---

## 4. Firestore with Cloud Run: Client Reuse

**Confidence: MEDIUM** (based on training data -- verify with current docs)

### Current Pattern (Correct)

The gym-tracker already does this correctly via the singleton pattern in `database.py:22-29`:

```python
db = None

def get_db():
    global db
    if db is None:
        db = firestore.Client()
    return db
```

This is the recommended pattern. The Firestore client:
- Manages its own gRPC connection pool internally
- Is thread-safe
- Should be reused across requests (not created per-request)
- Handles reconnection automatically

### Cloud Run Specific Considerations

| Aspect | Recommendation | Current Status |
|--------|---------------|----------------|
| Client reuse | Singleton pattern (one client per container) | CORRECT -- `get_db()` uses global singleton |
| Connection pooling | Handled internally by gRPC -- no manual pool needed | N/A -- automatic |
| Cold start | Firestore client creation adds ~200-500ms to cold start | Acceptable for Cloud Run |
| Warm connections | gRPC connections are kept alive between requests on the same container | Automatic |
| Concurrency | Thread-safe; gunicorn with 8 threads is fine | CORRECT -- 1 worker, 8 threads |
| Timeout | Set gunicorn timeout to match Cloud Run timeout | ISSUE -- currently `--timeout 0` (infinite) |

### Recommendations

1. **Keep the current singleton pattern** -- it is correct.
2. **Set gunicorn timeout to 60s** instead of 0 (infinite). This prevents stuck Firestore connections from blocking threads forever.
3. **Do NOT create a new `firestore.Client()` per request** -- this would open new gRPC channels each time, causing significant overhead.

---

## 5. N+1 Query Pattern Analysis & Cost Impact

**Confidence: HIGH** (based on direct codebase analysis)

### N+1 Patterns Found

#### Pattern A: Dashboard Stats (6 sub-queries from 1 API call)

`get_workout_dashboard_stats()` at line 677-692 calls:

```
get_workout_dashboard_stats(user_id)
  +-- get_weekly_workout_count(user_id)         -> 1 Firestore query
  +-- get_monthly_workout_count(user_id)
  |     +-- get_month_workouts(...)             -> 1 Firestore query
  +-- get_body_part_counts(user_id)
  |     +-- get_month_workouts(...)             -> 1 Firestore query (DUPLICATE)
  +-- get_neglected_parts(user_id)
  |     +-- get_body_part_counts(user_id)
  |           +-- get_month_workouts(...)       -> 1 Firestore query (TRIPLICATE)
  +-- get_most_trained_part(user_id)
  |     +-- get_body_part_counts(user_id)
  |           +-- get_month_workouts(...)       -> 1 Firestore query (4th time!)
  |     +-- (may also query previous month)     -> 1 more query
  +-- get_last_workout(user_id)                 -> 1 Firestore query
```

**Result: 5-6 Firestore queries, 3-4 of which fetch the exact same data.**

**Fix:** Fetch month workouts ONCE, pass the result to all sub-functions.

#### Pattern B: Weekly History Loop (12 separate queries)

`get_weekly_workout_history(weeks=12)` at line 699-746:

```python
for i in range(weeks - 1, -1, -1):    # 12 iterations
    docs = db.collection('workouts')   # 12 separate Firestore queries
        .where('date', '>=', start_str)
        .where('date', '<=', end_str)
        .stream()
```

**Result: 12 Firestore queries for data that could be fetched in 1 query** (fetch 84 days of data, then group by week in Python).

#### Pattern C: Full Collection Scans (no filters at all)

- `get_personal_records()` at line 1691: `db.collection('workouts').stream()` -- reads EVERY workout for EVERY user
- `get_progression()` at line 1731: `db.collection('workouts').order_by('date').stream()` -- same
- `export_all_workouts()` at line 1636: `db.collection('workouts').stream()` -- intentional (admin backup)
- `clear_hourly_occupancy()` at line 1616: `db.collection('hourly_occupancy').stream()` -- delete-all operation

### Cost Impact Summary

| Endpoint | Current Reads | Optimized Reads | Savings |
|----------|--------------|-----------------|---------|
| `/api/workouts/dashboard` | ~1,200 (10 users) | ~30 | 97% |
| `/api/analytics/weekly` | ~840 (12 queries x 70 docs) | ~210 (1 query, 84 days) | 75% |
| `/api/analytics/heatmap/2026` | ~3,650 | ~365 | 90% |
| `/api/strength` | entire collection | ~365 (1 year of user's workouts) | 90%+ |
| `/api/progression/<part>` | entire collection | ~365 | 90%+ |

---

## 6. Caching Strategies

**Confidence: MEDIUM** (some features may have changed since training cutoff)

### What Gym-Tracker Already Does

1. **In-memory `entries_cache`** in `app.py` -- caches latest occupancy reading (updated every 3 minutes by background thread). This is correct and efficient.

2. **`cached_data` parameter passing** in `get_extended_occupancy_stats()` -- fetches hourly data once and passes to sub-functions. This is the right pattern.

3. **Client-side cache** with 60s TTL (`statsCache`, `newYearCache` in dashboard.js). This prevents redundant API calls during normal browsing.

### Recommended Caching Layers

#### Layer 1: Application-Level Cache (Recommended -- Immediate Win)

Add a simple time-based cache for expensive, rarely-changing analytics:

```python
import time
from functools import lru_cache

# Simple TTL cache for analytics
_analytics_cache = {}
_cache_ttl = {}
CACHE_DURATION = 300  # 5 minutes

def cached_analytics(cache_key, fetch_fn, ttl=CACHE_DURATION):
    """Cache analytics results in memory with TTL."""
    now = time.time()
    if cache_key in _analytics_cache and now < _cache_ttl.get(cache_key, 0):
        return _analytics_cache[cache_key]
    
    result = fetch_fn()
    _analytics_cache[cache_key] = result
    _cache_ttl[cache_key] = now + ttl
    return result
```

**Good candidates for caching:**
| Data | TTL | Reason |
|------|-----|--------|
| Extended occupancy stats | 5 min | Occupancy updates every 3 minutes; caching avoids redundant Firestore reads between updates |
| Hourly/daily averages | 10 min | Averages over 30 days don't change rapidly |
| New Year effect stats | 1 hour | Historical data, changes once per day at most |
| Personal records | 5 min | Only changes when user logs a new PR |
| Heatmap data | 5 min per user | Only changes when a workout is added |

**Not good candidates:**
| Data | Reason |
|------|--------|
| Current workout for a date | Must be fresh -- user may have just saved it |
| Auth/login | Security-sensitive, must not be stale |
| Live occupancy count | Already cached via `entries_cache`, 3-minute cycle |

#### Layer 2: Firestore Bundled Queries (Not Recommended for This App)

Firestore Data Bundles package query results into a binary bundle that can be served from a CDN. This is designed for apps where many users need the same data (e.g., a product catalog).

**Not useful here because:**
- Most data is per-user (workouts, stats)
- The public data (occupancy) is already cached in-memory
- Adds complexity without benefit for a small-user app

#### Layer 3: Redis/Memcached (Not Recommended Yet)

Adding Redis would solve the caching problem perfectly but adds infrastructure:
- Another service to manage
- Cost (~$5-10/month for a small Memorystore instance)
- Not justified until the app outgrows in-memory caching

**When to add Redis:** If Cloud Run scales to multiple container instances (autoscaling > 1 instance), in-memory caches become per-instance and inconsistent. At that point, Redis becomes worthwhile.

#### Layer 4: Cloud Run Single-Instance Optimization

Since the app runs with `--workers 1 --threads 8` on a single Cloud Run instance:
- In-memory cache is shared across all 8 threads (Python GIL makes dict operations atomic)
- This is sufficient for the current scale
- Cache invalidation is simple (clear on write)

### Cache Invalidation Strategy

```python
def invalidate_user_cache(user_id):
    """Clear cached data for a specific user after a write operation."""
    keys_to_clear = [k for k in _analytics_cache if user_id in k]
    for key in keys_to_clear:
        _analytics_cache.pop(key, None)
        _cache_ttl.pop(key, None)

def invalidate_occupancy_cache():
    """Clear occupancy-related caches after scraper update."""
    keys_to_clear = [k for k in _analytics_cache if 'occupancy' in k or 'hourly' in k]
    for key in keys_to_clear:
        _analytics_cache.pop(key, None)
        _cache_ttl.pop(key, None)
```

---

## 7. Firestore Backup Best Practices

**Confidence: MEDIUM** (feature details may have evolved since training cutoff)

### Current Backup Approach

The app has manual export endpoints (`/api/admin/export-workouts`, `/api/admin/export-full`) that dump all data to JSON. These are admin-secret-protected but:
- Require manual triggering
- No scheduled backups
- No point-in-time recovery
- Export goes to HTTP response (no persistent storage)

### Recommended: Firestore Managed Export

Firestore has built-in export/import functionality that writes to Cloud Storage:

```bash
# Export entire database to Cloud Storage
gcloud firestore export gs://YOUR_BUCKET/backups/$(date +%Y-%m-%d)

# Export specific collections
gcloud firestore export gs://YOUR_BUCKET/backups/$(date +%Y-%m-%d) \
    --collection-ids=workouts,users,daily_entries,hourly_occupancy

# Import from backup
gcloud firestore import gs://YOUR_BUCKET/backups/2026-04-04
```

### Automated Backup Setup

**Option A: Cloud Scheduler + Cloud Functions (recommended)**

Create a Cloud Function triggered by Cloud Scheduler to run daily exports:

```python
# Cloud Function for scheduled Firestore backup
from google.cloud import firestore_admin_v1

def backup_firestore(event, context):
    client = firestore_admin_v1.FirestoreAdminClient()
    db_path = client.database_path('YOUR_PROJECT', '(default)')
    
    response = client.export_documents(request={
        'name': db_path,
        'output_uri_prefix': f'gs://YOUR_BUCKET/backups/{datetime.utcnow().strftime("%Y-%m-%d")}',
        'collection_ids': ['workouts', 'users', 'daily_entries', 'hourly_occupancy'],
    })
    return response
```

Schedule: `0 2 * * *` (daily at 2 AM)

**Option B: GitHub Actions scheduled workflow**

```yaml
name: Firestore Backup
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: |
          gcloud firestore export gs://${{ secrets.GCP_PROJECT_ID }}-backups/$(date +%Y-%m-%d) \
            --project=${{ secrets.GCP_PROJECT_ID }}
```

### Backup Cost Estimate

| Component | Cost |
|-----------|------|
| Export operation | Same as document reads (billed per doc read) |
| Cloud Storage | ~$0.02/GB/month (Standard class) |
| Gym-tracker data size | Likely <10 MB -- negligible storage cost |
| Daily backup | ~$0.01/day (reading all docs once) |

### Point-in-Time Recovery (PITR)

Firestore supports point-in-time recovery that allows restoring data to any point within the last 7 days (on the Blaze plan). This is enabled at the database level:

```bash
gcloud firestore databases update --type=firestore-native \
    --enable-pitr --project=YOUR_PROJECT
```

**Cost:** Additional storage charges for retained versions. For a small app, this is negligible.

**Recommendation:** Enable PITR as a safety net, plus run weekly managed exports to Cloud Storage for long-term retention.

---

## 8. Additional Optimization Patterns

### Pagination with `.limit()` and Cursors

The app never uses pagination. All queries use `.stream()` to iterate the full result set. For user-facing queries with bounded results, add `.limit()`:

```python
# Instead of streaming all and taking first match:
docs = db.collection('workouts') \
    .where('user_id', '==', user_id) \
    .where('date', '>=', month_ago) \
    .order_by('date', direction=firestore.Query.DESCENDING) \
    .limit(1) \                          # Only fetch 1 document
    .stream()
```

This saves document reads for queries that only need the first result (e.g., `get_last_workout()`).

### Batch Deletes with Firestore Batch Writes

The current `clear_hourly_occupancy()` deletes documents one at a time in a loop. Firestore batch writes can delete up to 500 documents per batch:

```python
def clear_hourly_occupancy() -> int:
    db = get_db()
    docs = db.collection('hourly_occupancy').stream()
    
    batch = db.batch()
    deleted = 0
    
    for doc in docs:
        batch.delete(doc.reference)
        deleted += 1
        if deleted % 500 == 0:  # Firestore batch limit
            batch.commit()
            batch = db.batch()
    
    if deleted % 500 != 0:
        batch.commit()
    
    return deleted
```

### Use `.select()` for Field Projection

When you only need specific fields, use `.select()` to reduce data transfer:

```python
# Only fetch date and body_parts fields (skip weight_data, notes, etc.)
docs = db.collection('workouts') \
    .where('user_id', '==', user_id) \
    .where('date', '>=', start_date) \
    .where('date', '<', end_date) \
    .select(['date', 'body_parts']) \     # Only these fields
    .stream()
```

This reduces network transfer but does NOT reduce the document read count (still billed per document). Useful for latency, not cost.

The app already uses this in one place: `database.py:369` for counting daily entries with `.select([])`.

### Aggregation Queries (COUNT, SUM, AVG)

Firestore added server-side aggregation queries (COUNT, SUM, AVG). These are billed at 1/1000th the cost of document reads. For counting operations, this is dramatically cheaper:

```python
from google.cloud.firestore_v1.aggregation import AggregationQuery

# Count workouts in a month -- 1000x cheaper than reading all docs
query = db.collection('workouts') \
    .where('user_id', '==', user_id) \
    .where('date', '>=', start_date) \
    .where('date', '<', end_date)

aggregate_query = AggregationQuery(query)
aggregate_query.count(alias='total')
results = aggregate_query.get()

count = results[0][0].value  # The count
```

**Applicable functions:**
- `get_weekly_workout_count()` -- only needs a count, not full documents
- `get_monthly_workout_count()` -- same
- `get_yearly_heatmap_data()` -- partially (needs body_parts count per date, not full docs)

### Document ID Design

The current workout document ID pattern `{user_id}_{date}` is good:
- Enables direct document lookup by user + date (no query needed for single-workout fetch)
- Prevents duplicate workouts per user per date (upsert semantics via `.set()`)
- The `get_workout()` function already uses this for O(1) lookups

However, sequential date-based IDs can cause write hotspots if many users write simultaneously (all writes go to the same tablet range). For the gym-tracker's scale (<10 concurrent writes), this is not an issue.

---

## 9. Prioritized Fix List

| Priority | Fix | Impact | Effort | Reads Saved |
|----------|-----|--------|--------|-------------|
| 1 | Add composite index on `workouts(user_id, date)` | Enables all other query fixes | 5 min | Prerequisite |
| 2 | Push `user_id` filter into Firestore queries (7 functions) | Eliminates N*users multiplier on reads | 1 hour | 80-90% per query |
| 3 | Fetch month workouts once in `get_workout_dashboard_stats()` | Eliminates 3-4 duplicate queries per dashboard load | 30 min | ~900 reads/load |
| 4 | Replace `get_weekly_workout_history()` loop with single range query | Reduces 12 queries to 1 | 30 min | ~700 reads/call |
| 5 | Add `user_id` filter to `get_personal_records()` and `get_progression()` | Prevents full collection scan | 15 min | 90%+ |
| 6 | Add in-memory TTL cache for analytics endpoints | Reduces Firestore reads for repeated requests | 1 hour | 80%+ for hot paths |
| 7 | Use `.limit(1)` in `get_last_workout()` after server-side filter | Stops reading after first match | 5 min | Variable |
| 8 | Use aggregation queries for pure count operations | 1000x cost reduction for counts | 30 min | Minimal count cost |
| 9 | Set up managed Firestore exports (backup) | Data safety | 1 hour | N/A |
| 10 | Batch deletes in `clear_hourly_occupancy()` | Faster delete, fewer round trips | 15 min | N/A (write ops) |

---

## Common Pitfalls

### Pitfall 1: Missing Composite Index at Runtime
**What goes wrong:** Query with `user_id` + `date` filters raises `FailedPrecondition` error in production.
**Why it happens:** Composite indexes must be created BEFORE the query code is deployed. Index building takes minutes.
**How to avoid:** Create the index first via console or `firestore.indexes.json`. Test locally. Deploy index changes before code changes.
**Warning signs:** Error message includes a URL to create the index -- check logs after first deploy.

### Pitfall 2: Firestore Client Created Per-Request
**What goes wrong:** Each request creates a new gRPC channel, adding 200-500ms latency.
**Why it happens:** Developer creates `firestore.Client()` inside a route handler instead of reusing.
**How to avoid:** Use the singleton pattern (already correct in this codebase).

### Pitfall 3: Unbounded Reads in Admin/Export Functions
**What goes wrong:** `export_full_backup()` reads every document in every collection. As data grows, this becomes slow and expensive.
**Why it happens:** Useful for small datasets, but doesn't scale.
**How to avoid:** For backups, use managed exports (`gcloud firestore export`). For user-facing exports, add pagination and collection-specific limits.

### Pitfall 4: Hotspot Writes from Sequential Document IDs
**What goes wrong:** If many users write workouts at the same time (e.g., January 1st), all document IDs start with the same date prefix, causing Firestore tablet splits.
**Why it happens:** Firestore distributes documents lexicographically across tablets.
**How to avoid:** The current pattern `{user_id}_{date}` disperses writes by user_id prefix, which is acceptable. Do NOT change to date-first IDs.

### Pitfall 5: Not Understanding Firestore's Billing Model
**What goes wrong:** Developer assumes "queries are cheap" without realizing every document returned costs a read operation.
**Why it happens:** Coming from SQL where a full table scan has no per-row billing.
**How to avoid:** Use the Firebase console's Usage tab to monitor read/write/delete counts. Set up billing alerts.

---

## Open Questions

1. **Firestore region:** The app deploys to `europe-central2` (Warsaw). Is the Firestore database also in `eur3` (Europe multi-region) or a single region? Multi-region costs ~40% more per operation. Check via `gcloud firestore databases describe`.

2. **Free tier status:** Is the project on the Spark (free) plan or Blaze (pay-as-you-go)? The free tier includes 50K reads/day. At current usage patterns, the app may be exceeding this and incurring unexpected charges.

3. **Aggregation query availability:** Firestore aggregation queries (COUNT, SUM, AVG) were GA as of mid-2023, but the Python SDK version `>=2.19.0` should support them. Verify with the installed version.

4. **PITR availability:** Point-in-time recovery requires the Blaze plan and may not be available in all regions. Verify for `europe-central2`.

---

## Sources

### Primary (MEDIUM confidence -- training data, not live verification)
- Google Cloud Firestore pricing page (https://cloud.google.com/firestore/pricing) -- pricing figures from training data, verify current values
- Google Cloud Firestore documentation on queries and indexes (https://cloud.google.com/firestore/docs/query-data/queries) -- stable API, likely current
- Google Cloud Firestore best practices (https://cloud.google.com/firestore/docs/best-practices) -- architectural guidance, stable

### Codebase Analysis (HIGH confidence)
- `database.py` -- all 2,060 lines reviewed, all 21 `.stream()` calls catalogued, all 7 client-side filtering instances identified
- `app.py` -- API endpoint patterns and dashboard stats aggregation analyzed
- `.planning/codebase/CONCERNS.md` -- cross-referenced with existing M-02 and TD-04 findings

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Client-side filtering anti-pattern | HIGH | Direct codebase evidence, well-documented Firestore best practice |
| Composite index requirements | HIGH | Stable Firestore feature, well-documented behavior |
| N+1 query patterns | HIGH | Direct codebase evidence, traceable call chains |
| Pricing figures | MEDIUM | From training data (May 2025); may have changed |
| Aggregation query API | MEDIUM | Feature was GA by mid-2023, but exact Python SDK API should be verified |
| Backup/PITR features | MEDIUM | Feature availability by region and plan should be verified |
| Alternative database comparison | MEDIUM | Based on general knowledge of each platform |

---

*Research date: 2026-04-04*
*Valid until: 2026-05-04 (pricing should be reverified; API patterns are stable)*
