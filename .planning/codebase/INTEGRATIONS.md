# External Integrations

**Analysis Date:** 2026-04-04

## Databases & Storage

### Google Cloud Firestore

**Role:** Primary and only database. NoSQL document store.

**Client initialization** (`database.py` lines 22-29):
```python
from google.cloud import firestore
db = None
def get_db():
    global db
    if db is None:
        db = firestore.Client()
    return db
```

**Authentication:** Implicit via GCP service account. On Cloud Run, uses the service's identity. In CI, `GCP_SA_KEY` secret provides credentials JSON. Locally, requires `GOOGLE_APPLICATION_CREDENTIALS` env var or `gcloud auth application-default login`.

**Collections:**

| Collection | Document ID Pattern | Purpose | Key Fields |
|------------|-------------------|---------|------------|
| `users` | UUID string (e.g., `admin`) | User accounts | `user_id`, `username`, `username_lower`, `password_hash`, `created_at` |
| `daily_entries` | `YYYY-MM-DD` | Daily gym occupancy snapshots | `date`, `entries_count`, `last_updated`, `weekday` |
| `hourly_occupancy` | `YYYY-MM-DD_HH` | Per-hour occupancy data | `date`, `hour`, `occupancy`, `weekday` |
| `workouts` | `{user_id}_{YYYY-MM-DD}` | User workout logs | `date`, `user_id`, `body_parts[]`, `weight_data{}`, `notes`, `created_at` |

**Access patterns:**
- Write: `doc_ref.set(data)` -- always full document overwrites (no partial updates except password reset)
- Read: `.where()` queries with `.stream()` iteration; `.document(id).get()` for single lookups
- Delete: `.document(id).delete()` for individual workout removal
- Batch delete: Manual loop with `.stream()` + `.delete()` in `clear_hourly_occupancy()`
- No transactions or batch writes used
- No indexes explicitly defined (relies on Firestore automatic single-field indexes)
- No pagination -- all queries use `.stream()` to iterate full result sets

**Key database functions** (`database.py`):
- `save_daily_entry()` -- Upserts daily occupancy count
- `save_hourly_occupancy()` -- Records occupancy per hour slot
- `save_workout()` / `get_workout()` / `delete_workout()` -- CRUD for workout logs
- `get_month_workouts()` -- Range query by date for a month
- `get_weekly_workout_history()` -- Aggregates workouts over last N weeks
- `get_yearly_heatmap_data()` -- Full year query for heatmap visualization
- `get_hourly_stats()` -- Aggregates hourly data for "best hours" analysis
- `get_extended_occupancy_stats()` -- Daily averages by weekday
- `export_all_workouts()` / `export_full_backup()` -- Full data export for admin

### File Storage

None. No file uploads, no blob storage. All data lives in Firestore.

### Caching

**In-memory only** (no Redis, no Memcached):
- `entries_cache` dict in `app.py` (line 115) -- Caches current gym occupancy
- `statsCache` and `newYearCache` in `static/js/dashboard.js` -- Client-side JS cache with 60s TTL
- Flask-Limiter uses `storage_uri="memory://"` -- Rate limit counters lost on restart

## External APIs & Services

### eFitness CMS Portal (Web Scraping)

**Purpose:** Source of real-time gym occupancy data. This is a web scraping integration, not an API.

**Target:** Configurable via `GYM_URL` env var (e.g., `https://your-gym.cms.efitness.com.pl`)

**Authentication flow** (`app.py` lines 127-168):
1. Create `requests.Session` with browser-like User-Agent headers
2. GET the gym URL to establish cookies
3. POST to `{GYM_URL}/Login/SystemLogin` with `Login` (email) and `Password` form fields
4. Session cookies maintained for subsequent requests

**Data extraction** (`app.py` lines 183-255):
1. GET `{GYM_URL}/na-terenie-klubu` (members currently in the gym)
2. Parse HTML with BeautifulSoup
3. Regex search for pattern `Aktualnie w klubie N / M` to extract current count
4. Fallback: search for any `N / M` pattern where M > 50

**Polling schedule:**
- Background thread (`background_updater`) fetches every 180 seconds (3 minutes)
- Manual refresh via `/api/refresh` with 30-second cooldown
- Session re-login on redirect detection (expired session handling)

**Error handling:**
- 15-second request timeout (`REQUEST_TIMEOUT`)
- Session expiry detection via login page redirect
- Graceful degradation: if scraping fails, cache retains last known data with error status

**Credentials:** `GYM_EMAIL` and `GYM_PASSWORD` env vars

### Google Fonts CDN

**Usage:** Inter font family loaded in `templates/dashboard.html`
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### CDN Resources (Content Security Policy allows)

Allowed in CSP header (`app.py` lines 978-989):
- `https://cdn.jsdelivr.net` -- Script source (e.g., Chart.js or similar)
- `https://cdnjs.cloudflare.com` -- Script source
- `https://fav.farm` -- Favicon/emoji images

## Third-Party Libraries (with versions)

### Python Backend

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| `flask` | `>=3.1.0` | Web framework | `app.py` |
| `flask-cors` | `>=6.0.0` | CORS middleware | `app.py` line 58 |
| `flask-limiter` | `>=3.8.0` | Rate limiting | `app.py` lines 61-68 |
| `flask-compress` | `>=1.17` | GZIP compression | `app.py` line 72 |
| `requests` | `>=2.32.4` | HTTP client for scraping | `app.py` lines 136-154 |
| `beautifulsoup4` | `>=4.12.3` | HTML parsing | `app.py` line 215 |
| `gunicorn` | `>=23.0.0` | Production WSGI server | `Dockerfile` CMD |
| `pytz` | `>=2024.2` | Timezone (Europe/Warsaw) | `app.py`, `database.py` |
| `google-cloud-firestore` | `>=2.19.0` | Firestore SDK | `database.py` line 6 |
| `bcrypt` | `>=4.2.0` | Password hashing | `database.py` lines 157-168 |
| `urllib3` | `>=2.5.0` | Pinned for security | transitive |
| `protobuf` | `>=5.29.0` | Pinned for security | transitive (Firestore) |
| `werkzeug` | `>=3.1.3` | Pinned for security | transitive (Flask) |
| `zipp` | `>=3.21.0` | Pinned for security | transitive |
| `certifi` | `>=2024.12.14` | Pinned for security | transitive (requests) |

### Frontend (Vanilla JS)

| Library | Version | Purpose | Location |
|---------|---------|---------|----------|
| DOMPurify | Bundled (minified) | XSS sanitization | `static/js/purify.min.js` |

### Stats Dashboard Prototype (React)

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | `^19.2.0` | UI framework |
| `react-dom` | `^19.2.0` | DOM renderer |
| `lucide-react` | `^0.562.0` | Icon components |
| `clsx` | `^2.1.1` | Conditional classnames |
| `tailwind-merge` | `^3.4.0` | Tailwind class deduplication |
| `vite` | `^7.2.4` | Build tool |
| `tailwindcss` | `^4.1.18` | Utility CSS |
| `typescript` | `~5.9.3` | Type checking |
| `eslint` | `^9.39.1` | Linting |

## CI/CD & DevOps Tools

### GitHub Actions

**Deploy Pipeline** (`.github/workflows/deploy.yml`):
- Trigger: Push to `main` branch
- Actions used:
  - `actions/checkout@v4`
  - `google-github-actions/auth@v2` -- Authenticates with GCP via service account key JSON
  - `google-github-actions/deploy-cloudrun@v2` -- Source-based deploy (Cloud Build builds the Docker image)
- Deploys to: Cloud Run service `gym-tracker` in `europe-central2`
- Env vars injected: `SECRET_KEY`

**Security Scan Pipeline** (`.github/workflows/security-scan.yml`):
- Trigger: Push/PR to main + daily cron (`0 0 * * *`)
- Actions/tools used:
  - `actions/checkout@v4` (with `fetch-depth: 0` for full history)
  - `gitleaks/gitleaks-action@v2` -- Secret scanning across git history
  - `actions/setup-python@v5` (Python 3.11 for scanning tools)
  - `safety` -- Python dependency vulnerability check (`safety check --full-report`)
  - `pip-audit` -- Python dependency audit (`pip-audit --strict`)
- Both audit steps use `continue-on-error: true` (non-blocking)

### Pre-commit Hooks (`.pre-commit-config.yaml`)

| Hook | Source | Version | Purpose |
|------|--------|---------|---------|
| `trailing-whitespace` | `pre-commit-hooks` | v4.5.0 | Remove trailing whitespace |
| `end-of-file-fixer` | `pre-commit-hooks` | v4.5.0 | Ensure files end with newline |
| `check-yaml` | `pre-commit-hooks` | v4.5.0 | Validate YAML syntax |
| `check-added-large-files` | `pre-commit-hooks` | v4.5.0 | Block large file commits |
| `gitleaks` | `gitleaks` | v8.18.1 | Secret detection in staged changes |

### Google Cloud Platform Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Cloud Run** | Container hosting | 1 worker, 8 threads, unauthenticated access |
| **Cloud Build** | Docker image build | Triggered by Cloud Run source deploy |
| **Firestore** | NoSQL database | Native mode, default database |
| **IAM** | Service account auth | `GCP_SA_KEY` for CI, implicit identity on Cloud Run |

## Authentication & Identity

**Custom implementation** -- No third-party auth provider (no Firebase Auth, no Auth0, no OAuth).

**Architecture:**
- Server-side Flask sessions (signed cookies via `app.secret_key`)
- Password hashing: bcrypt with automatic salt generation (`database.py` lines 157-168)
- User storage: Firestore `users` collection
- Session lifetime: 365 days, Secure + HttpOnly + SameSite=Lax cookies

**Admin authentication:**
- Admin API endpoints protected by `ADMIN_SECRET` env var
- Passed via `X-Admin-Secret` header or `secret` query parameter
- Timing-safe comparison using `secrets.compare_digest()` (`app.py` line 723)

**Endpoints:**
- `POST /api/auth/register` -- Create account (rate limited: 5/min)
- `POST /api/auth/login` -- Authenticate (rate limited: 10/min)
- `POST /api/auth/logout` -- Clear session
- `GET /api/auth/me` -- Check session validity

## Monitoring & Observability

**Error Tracking:** None (no Sentry, no Datadog, no Cloud Error Reporting configured)

**Logging:**
- Python `print()` statements throughout `app.py` for scraping status
- Python `logging` module used in `database.py` (`logger = logging.getLogger(__name__)`)
- Gunicorn logs to stdout (captured by Cloud Run Logs)
- No structured logging format

**Health Check:** `GET /health` endpoint returns `{'status': 'healthy', 'timestamp': ...}` (`app.py` line 945)

## Webhooks & Callbacks

**Incoming:** None

**Outgoing:** None

## Environment Configuration

**Required env vars for production:**
- `GYM_URL`, `GYM_EMAIL`, `GYM_PASSWORD` -- Gym portal access
- `SECRET_KEY` -- Flask session signing
- `ADMIN_SECRET` -- Admin API access
- `PORT` -- Set by Cloud Run automatically

**`.env` file present** -- Contains local development configuration. `.env.example` provides template with all variable documentation.

**Secrets in GitHub Actions:**
- `GCP_PROJECT_ID` -- Google Cloud project identifier
- `GCP_SA_KEY` -- Service account credentials JSON blob
- `SECRET_KEY` -- Injected as Cloud Run env var during deploy

---

*Integration audit: 2026-04-04*
