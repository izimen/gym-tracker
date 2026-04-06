# Technology Stack

**Analysis Date:** 2026-04-04

## Languages & Runtimes

**Primary: Python 3.12**
- Backend server, scraping, database access, authentication
- Runtime: CPython 3.12 on Alpine Linux (Docker)
- Key files: `app.py` (1012 LOC), `database.py` (2060 LOC)

**Secondary: JavaScript (Vanilla ES6+)**
- Frontend UI for dashboard, calendar, and home pages
- No build step -- served directly as static files by Flask
- Key files: `static/js/dashboard.js` (1457 LOC), `static/js/calendar.js` (583 LOC), `static/js/home.js` (253 LOC)

**Secondary: TypeScript ~5.9**
- Used only in `stats-dashboard/` React prototype (separate sub-project)
- Strict mode enabled, path aliases configured (`@/*` -> `./src/*`)
- Config: `stats-dashboard/tsconfig.json`, `stats-dashboard/tsconfig.app.json`

**Markup/Styling:**
- HTML templates with inline CSS in Jinja2 (`.html` files in `templates/`)
- Separate CSS files in `static/css/` (`dashboard.css`, `calendar.css`, `home.css`)
- Tailwind CSS 4.x in `stats-dashboard/` prototype only

## Frameworks & Libraries

### Backend (Python)

**Core:**
- **Flask** `>=3.1.0` -- Web framework, routing, templates, sessions
  - Entry point: `app.py` line `app = Flask(__name__)`
  - Jinja2 templates in `templates/`
  - Static files served from `static/`
- **Gunicorn** `>=23.0.0` -- WSGI server for production
  - Config: 1 worker, 8 threads, timeout disabled for Cloud Run
  - Invoked via `Dockerfile` CMD: `gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app`

**Flask Extensions:**
- **flask-cors** `>=6.0.0` -- Cross-origin request handling, configured per `ALLOWED_ORIGINS` env var
- **flask-limiter** `>=3.8.0` -- Rate limiting (in-memory storage), default 1000/day + 150/hour
- **flask-compress** `>=1.17` -- GZIP response compression

**Scraping:**
- **requests** `>=2.32.4` -- HTTP client for eFitness portal scraping
- **beautifulsoup4** `>=4.12.3` -- HTML parsing to extract gym occupancy numbers

**Database:**
- **google-cloud-firestore** `>=2.19.0` -- Firestore client SDK

**Authentication:**
- **bcrypt** `>=4.2.0` -- Password hashing (gensalt + hashpw)

**Utilities:**
- **pytz** `>=2024.2` -- Timezone handling (hardcoded to `Europe/Warsaw`)

**Security-pinned transitive dependencies:**
- `urllib3>=2.5.0`, `protobuf>=5.29.0`, `werkzeug>=3.1.3`, `zipp>=3.21.0`, `certifi>=2024.12.14`

### Frontend (Vanilla JS)

**No framework.** Plain JavaScript with `fetch()` API calls.
- **DOMPurify** -- XSS sanitization for dynamic HTML, loaded as `static/js/purify.min.js`
- **Google Fonts** -- Inter font loaded from CDN (`fonts.googleapis.com`)

### Stats Dashboard Prototype (React/TypeScript)

Located in `stats-dashboard/` -- a separate sub-project, not integrated into the main app.

**Dependencies:**
- **React** `^19.2.0` + **react-dom** `^19.2.0`
- **lucide-react** `^0.562.0` -- Icon library
- **clsx** `^2.1.1` + **tailwind-merge** `^3.4.0` -- Utility class helpers

**Dev Dependencies:**
- **Vite** `^7.2.4` -- Build tool, config at `stats-dashboard/vite.config.ts`
- **TypeScript** `~5.9.3`
- **Tailwind CSS** `^4.1.18` via `@tailwindcss/vite` plugin
- **ESLint** `^9.39.1` with `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `typescript-eslint`
- **@vitejs/plugin-react** `^5.1.1`

**Path alias:** `@` maps to `stats-dashboard/src/` (configured in both `vite.config.ts` and `tsconfig.json`)

## Build & Development Tools

**Package Management:**
- Python: `pip` with `requirements.txt` (no lockfile -- uses `>=` version specifiers)
- Node.js: `npm` for `stats-dashboard/` (lockfile not checked)

**Pre-commit Hooks** (`.pre-commit-config.yaml`):
- `pre-commit-hooks` v4.5.0: trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files
- `gitleaks` v8.18.1: Secret detection (runs `detect --source . --verbose`)

**Linting/Formatting:**
- Python: None configured (no flake8, black, ruff, etc.)
- JS/TS: ESLint in `stats-dashboard/` only; no linting for vanilla JS in `static/js/`

**Local Development:**
- `setup_server.sh` -- Ubuntu setup script: installs Python 3, creates venv, installs deps, configures systemd service on port 5000
- Direct run: `python app.py` starts Flask dev server on `0.0.0.0:5000`
- Stats dashboard: `npm run dev` (Vite dev server)

**No test framework detected.** No test files, no pytest/unittest config, no vitest config.

## Infrastructure & Deployment

**Container:**
- `Dockerfile` based on `python:3.12-alpine`
- Single-stage build, no multi-stage optimization
- Copies entire project into `/app`, installs deps, runs gunicorn

**Cloud Platform: Google Cloud**
- **Cloud Run** -- Serverless container hosting
  - Region: `europe-central2`
  - Service name: `gym-tracker`
  - Flags: `--allow-unauthenticated --clear-base-image`
  - Source-based deploy (Cloud Build triggered automatically)
- **Firestore** -- NoSQL document database (native mode)
  - Authentication via GCP service account (implicit on Cloud Run, `GCP_SA_KEY` in CI)

**CI/CD: GitHub Actions**

1. **Deploy workflow** (`.github/workflows/deploy.yml`):
   - Trigger: push to `main`
   - Steps: checkout -> GCP auth (service account key) -> deploy to Cloud Run via `google-github-actions/deploy-cloudrun@v2`
   - Injects `SECRET_KEY` as env var

2. **Security scan workflow** (`.github/workflows/security-scan.yml`):
   - Trigger: push/PR to main + daily cron at midnight
   - Steps: Gitleaks secret scan, `safety check`, `pip-audit`
   - Both audit steps use `continue-on-error: true`

**Required Secrets (GitHub Actions):**
- `GCP_PROJECT_ID` -- Google Cloud project ID
- `GCP_SA_KEY` -- Service account credentials JSON
- `SECRET_KEY` -- Flask session signing key
- `GITHUB_TOKEN` -- For Gitleaks (auto-provided)

## Configuration

**Environment Variables** (see `.env.example`):

| Variable | Purpose | Required |
|----------|---------|----------|
| `GYM_URL` | eFitness portal base URL | Yes |
| `GYM_EMAIL` | Portal login email | Yes |
| `GYM_PASSWORD` | Portal login password | Yes |
| `SECRET_KEY` | Flask session secret | Yes (prod) |
| `ADMIN_SECRET` | Admin API authentication | Yes |
| `ADMIN_PASSWORD` | Initial admin user password | No (auto-generated) |
| `ALLOWED_ORIGINS` | CORS whitelist (comma-separated) | No (defaults to localhost) |
| `PORT` | Server port | No (default: 5000) |

**Session Configuration:**
- Cookie: Secure, HttpOnly, SameSite=Lax
- Lifetime: 365 days (permanent sessions)
- Secret key: from `SECRET_KEY` env var, falls back to file-based persistence at `$APP_HOME/.flask_secret`

**Rate Limits (flask-limiter, in-memory):**
- Global: 1000/day, 150/hour
- `/api/auth/register`: 5/minute
- `/api/auth/login`: 10/minute
- `/api/analytics/*`: 100/hour
- `/api/occupancy`, `/api/entries`: 200/hour

---

*Stack analysis: 2026-04-04*
