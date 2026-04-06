# Project Structure

**Analysis Date:** 2026-04-04

## Directory Tree (annotated)

```
gym-tracker/
├── .claude/                        # Claude Code local settings
│   └── settings.local.json
├── .github/
│   └── workflows/
│       ├── deploy.yml              # Cloud Run auto-deploy on push to main
│       └── security-scan.yml       # Security scanning workflow
├── .planning/
│   └── codebase/                   # GSD codebase analysis docs (this file)
├── AUDIT/                          # Previous code audit reports (13 files)
│   ├── 00_EXECUTIVE_SUMMARY.md
│   ├── 01_REPO_MAP.md
│   └── ... (02-13)
├── design-showcase/                # Static HTML design mockups (NOT live)
│   ├── index.html                  # Index listing all variants
│   ├── statistics-v2-*.html        # Statistics page design explorations
│   └── variant-*.html              # Dashboard design variants (a/b/c/current)
├── scripts/
│   └── security/
│       ├── scan_secrets.sh         # Secret scanning utility
│       ├── security_audit.sh       # Security audit runner
│       └── validate_env.sh         # Environment variable validation
├── static/
│   ├── css/
│   │   ├── dashboard.css           # Dashboard page styles (1012 LOC)
│   │   ├── calendar.css            # Calendar page styles (728 LOC)
│   │   └── home.css                # Legacy home page styles (493 LOC)
│   └── js/
│       ├── dashboard.js            # Main dashboard logic (1457 LOC) -- THE primary frontend file
│       ├── calendar.js             # Standalone calendar page logic (583 LOC)
│       ├── home.js                 # Legacy home page logic (253 LOC)
│       └── purify.min.js           # DOMPurify library (vendored/minified)
├── stats-dashboard/                # React prototype (NOT connected to backend)
│   ├── src/
│   │   ├── App.tsx                 # Root component (renders StatisticsPage)
│   │   ├── main.tsx                # React entry point
│   │   ├── components/
│   │   │   ├── charts/             # DailyChart, HourlyChart, WeeklyChart, YearlyHeatmap
│   │   │   ├── layout/             # FloatingDock
│   │   │   ├── statistics/         # BestWorstTimes, MonthComparison, NewYearEffect
│   │   │   └── ui/                 # Card, StatsCard
│   │   ├── lib/
│   │   │   └── utils.ts            # cn() utility (clsx + tailwind-merge)
│   │   └── pages/
│   │       └── StatisticsPage.tsx  # Main statistics page (209 LOC)
│   ├── package.json                # React 19, Vite 7, Tailwind 4
│   └── vite.config.ts
├── templates/
│   ├── dashboard.html              # Main dashboard page (541 LOC) -- served at /
│   ├── calendar.html               # Standalone calendar page (1433 LOC) -- served at /calendar
│   └── index.html                  # Legacy home page (852 LOC) -- served at /legacy
├── tests/
│   └── security_tests.py           # Security test suite
├── app.py                          # Flask server: routing, scraping, security (1012 LOC)
├── database.py                     # Firestore data layer: auth, CRUD, analytics (2060 LOC)
├── Dockerfile                      # Python 3.12 Alpine + gunicorn
├── requirements.txt                # Python dependencies (pinned with >=)
├── .env                            # Environment variables (EXISTS -- DO NOT READ)
├── .env.example                    # Template for required env vars
├── .pre-commit-config.yaml         # Pre-commit hooks config
├── .dockerignore                   # Docker build exclusions
├── .gitignore                      # Git ignore rules
├── setup_server.sh                 # Server setup script
├── uruchom.bat                     # Windows launch script (Polish: "run")
├── dashboard_old.html              # Dead: previous dashboard version (540 LOC)
├── response.html                   # Dead: scraped HTML response sample (612 LOC)
├── zmiany.md                       # Dead: changelog notes (Polish: "changes")
├── LICENSE                         # Project license
├── README.md                       # Project readme
└── SECURITY.md                     # Security policy
```

## Module Roles

### Backend (Python -- project root)

**`app.py`** -- The single Flask application file. Contains ALL server-side logic:
- Route definitions for every endpoint (~40 routes across occupancy, workouts, analytics, auth, admin, export, debug)
- Background scraper thread and gym session management
- In-memory cache (`entries_cache` dict, `current_session`, locks)
- Security middleware (`add_security_headers`, `enforce_https`, rate limiter)
- CORS, compression, session configuration

**`database.py`** -- The Firestore abstraction layer. Contains ALL database operations:
- User management (CRUD, bcrypt auth, admin functions)
- Workout tracking (save, get, delete, monthly queries, body part counts)
- Occupancy analytics (hourly averages, daily averages, best/worst times, new year effect)
- Data quality (`is_complete_day`, `is_gym_open`, `GYM_HOURS` config)
- Configuration constants (`BODY_PARTS` dict with Polish names, emojis, colors)
- Export/backup functions

### Frontend (JavaScript + HTML + CSS)

Each page is a fully self-contained unit with its own HTML template, CSS file, and JS file. There is NO shared base template, NO shared CSS, and NO shared JS modules.

**Dashboard** (`templates/dashboard.html` + `static/js/dashboard.js` + `static/css/dashboard.css`):
- Primary user-facing page served at `/`
- Tabbed interface: Trening (workout calendar), Statystyki (occupancy analytics), Sila (strength tracking)
- Login/register overlay (auth required)
- Contains inline CSS in the HTML `<style>` block (541 LOC HTML includes extensive inline styles)
- External CSS in `dashboard.css` covers calendar, modal, charts, statistics, heatmap, strength tab
- JS covers: auth, live counter, calendar, workout modal, statistics charts, heatmap, comparison, export, strength/progression

**Calendar** (`templates/calendar.html` + `static/js/calendar.js` + `static/css/calendar.css`):
- Standalone calendar page served at `/calendar`
- Duplicates workout calendar and modal logic from dashboard.js
- Does NOT have auth overlay -- relies on server-side session being already set
- Inline CSS in HTML (1433 LOC includes heavy inline styling)

**Legacy Home** (`templates/index.html` + `static/js/home.js` + `static/css/home.css`):
- Simple occupancy display served at `/legacy`
- Shows live count, week-ago comparison, weekday average
- Manual refresh button with 30s cooldown
- No auth required

### React Prototype (`stats-dashboard/`)

- Standalone Vite + React 19 + TypeScript + Tailwind 4 SPA
- Contains chart components that visually mirror the dashboard's statistics tab
- Uses hardcoded/mock data -- has NO API integration with the Flask backend
- NOT served by the Flask app, NOT deployed
- Appears to be a design exploration for a future statistics UI rewrite

## Key File Locations

**Entry Points:**
- `app.py:1002-1009`: Flask server startup (`__main__` block)
- `app.py:266-267`: Background scraper thread start
- `static/js/dashboard.js:1457`: Dashboard page init call
- `static/js/calendar.js:23-28`: Calendar page init
- `static/js/home.js:53-60`: Legacy page data fetch

**Configuration:**
- `app.py:91-96`: Environment variable loading (GYM_EMAIL, GYM_PASSWORD, ADMIN_SECRET, GYM_URL)
- `app.py:30-53`: Session and cookie configuration
- `app.py:57-58`: CORS allowed origins
- `app.py:60-68`: Rate limiter setup
- `database.py:41-44`: Gym hours configuration (`GYM_HOURS` dict)
- `database.py:395-404`: Body parts configuration (`BODY_PARTS` dict)
- `.env.example`: Template for all required env vars
- `Dockerfile`: Production container config (Python 3.12 Alpine, gunicorn)
- `.github/workflows/deploy.yml`: Cloud Run deployment config

**Core Logic:**
- `app.py:183-255`: `fetch_entries_data()` -- scraper core logic
- `app.py:127-168`: `get_gym_session()` -- eFitness session management
- `database.py:171-211`: `create_user()` -- user registration
- `database.py:214-244`: `authenticate_user()` -- login verification
- `database.py:435-469`: `save_workout()` -- workout persistence
- `database.py:854-889`: `save_hourly_occupancy()` -- hourly data recording
- `database.py:919-999`: `get_hourly_averages()` -- hourly entries calculation
- `database.py:1171-1235`: `get_daily_averages()` -- daily max occupancy per weekday
- `database.py:1569-1602`: `get_extended_occupancy_stats()` -- optimized aggregate stats endpoint

**Testing:**
- `tests/security_tests.py`: Security-focused tests

**Security:**
- `app.py:955-999`: Security headers, CSP, caching policies
- `scripts/security/scan_secrets.sh`: Secret detection
- `scripts/security/security_audit.sh`: Audit runner
- `scripts/security/validate_env.sh`: Env var checker

## Naming Conventions

**Files:**
- Python: `snake_case.py` (e.g., `database.py`, `security_tests.py`)
- JavaScript: `camelCase.js` matching page name (e.g., `dashboard.js`, `calendar.js`, `home.js`)
- CSS: `camelCase.css` matching page name (e.g., `dashboard.css`, `calendar.css`, `home.css`)
- HTML templates: `camelCase.html` (e.g., `dashboard.html`, `calendar.html`, `index.html`)

**Directories:**
- Standard Flask convention: `templates/`, `static/`, `static/js/`, `static/css/`
- Lowercase with hyphens for non-code dirs: `design-showcase/`, `stats-dashboard/`

## Where to Add New Code

**New API Endpoint:**
- Add route handler in `app.py` under the appropriate section comment block (workouts, analytics, auth, admin, export)
- Add database function in `database.py` under the matching section
- Follow pattern: route calls `require_login()` -> calls `database.function(user_id)` -> returns `jsonify(result)`
- Apply rate limiting with `@limiter.limit()` decorator
- Admin endpoints: guard with `secrets.compare_digest(secret, ADMIN_SECRET)`

**New Frontend Feature (on Dashboard):**
- Add HTML structure in `templates/dashboard.html`
- Add styles in `static/css/dashboard.css`
- Add JS logic in `static/js/dashboard.js` -- follow the section comment pattern (`// ============ SECTION NAME ============`)
- Use `authFetch()` wrapper for authenticated API calls
- Use `safeSanitize()` for any user-generated HTML content

**New Firestore Collection:**
- Define collection access functions in `database.py`
- Use `get_db()` helper to obtain Firestore client
- Follow existing document ID patterns (date-based: `YYYY-MM-DD` or composite: `{user_id}_{date}`)
- Add export function for backup support

**New Page:**
- Create `templates/{page}.html` (self-contained, no shared base)
- Create `static/js/{page}.js` and `static/css/{page}.css`
- Add route in `app.py`: `@app.route('/page') def page(): return render_template('page.html')`
- Note: each page must include its own complete HTML boilerplate, CSS variables, and DOMPurify script tag

**New Python Dependency:**
- Add to `requirements.txt` with minimum version pin (`>=`)
- Test with `pip install -r requirements.txt`

## Special Directories

**`AUDIT/`:**
- Purpose: Contains 13 audit report documents from a previous comprehensive code review
- Generated: Manually by AI audit
- Committed: Yes
- Note: Reference material only; not consumed by the application

**`design-showcase/`:**
- Purpose: Static HTML mockups exploring different UI designs for the statistics page
- Generated: Manually during design phase
- Committed: Yes
- Note: Pure HTML files with inline CSS, no backend integration; serve as visual references only

**`stats-dashboard/`:**
- Purpose: React/TypeScript/Tailwind prototype for a potential statistics UI rewrite
- Generated: No (active code, but not integrated)
- Committed: Yes (including `node_modules` in `.gitignore`)
- Note: NOT connected to Flask backend. Uses mock/hardcoded data. Would need API proxy configuration via `vite.config.ts` to connect.

**`scripts/security/`:**
- Purpose: Bash scripts for security scanning and environment validation
- Generated: No
- Committed: Yes
- Note: Meant for developer use; not part of CI pipeline

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents used by planning and execution commands
- Generated: By Claude agents
- Committed: Varies by workflow

## Dead/Legacy Files

**`dashboard_old.html`** (540 LOC):
- Previous version of the dashboard page
- Replaced by `templates/dashboard.html`
- Not served by any route; safe to delete

**`response.html`** (612 LOC):
- Sample HTML response from the eFitness scraper
- Used during development for testing HTML parsing
- Not served or referenced; safe to delete

**`zmiany.md`**:
- Changelog/notes file (Polish: "changes")
- Not referenced by application code; superseded by git history

**`templates/index.html`** + `static/js/home.js` + `static/css/home.css`:
- Served at `/legacy` route -- still accessible but superseded by dashboard
- The route name itself (`/legacy`) indicates it's kept for backward compatibility
- Contains only basic occupancy display without auth or workout features

**`templates/calendar.html`** + `static/js/calendar.js` + `static/css/calendar.css`:
- Served at `/calendar` -- accessible standalone page
- Most calendar functionality is now duplicated inside `dashboard.js`/`dashboard.html`
- The standalone calendar page lacks the login overlay present in the dashboard

---

*Structure analysis: 2026-04-04*
