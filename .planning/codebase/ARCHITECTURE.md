# System Architecture

**Analysis Date:** 2026-04-04

## Overview Diagram (ASCII)

```
                        +-------------------+
                        |   eFitness Portal  |
                        |  (gym website)     |
                        +--------+----------+
                                 |
                          HTML scraping
                          (requests + BS4)
                                 |
+------------------------------- | ----------------------------------------+
|  Flask Monolith (app.py)       v                                         |
|                                                                          |
|  +-------------------+   +--------------------+   +-------------------+  |
|  | Background Thread |   | Route Handlers     |   | Security Layer   |  |
|  | (scraper loop)    |-->| /api/occupancy     |   | - rate limiter   |  |
|  | every 3 minutes   |   | /api/entries       |   | - CSP headers    |  |
|  +-------------------+   | /api/stats         |   | - CORS           |  |
|         |                | /api/workout/*     |   | - HTTPS enforce  |  |
|         v                | /api/analytics/*   |   +-------------------+  |
|  +-------------------+   | /api/auth/*        |                          |
|  | In-Memory Cache   |   | /api/admin/*       |                          |
|  | (entries_cache)   |   | /api/export/*      |                          |
|  | (session/locks)   |   | /api/strength      |                          |
|  +-------------------+   | /api/progression/* |                          |
|                          +--------+-----------+                          |
|                                   |                                      |
+-----------------------------------|--------------------------------------+
                                    |
                          database.py (Firestore client)
                                    |
                        +-----------v-----------+
                        |  Google Cloud Firestore |
                        |  Collections:           |
                        |  - daily_entries        |
                        |  - hourly_occupancy     |
                        |  - workouts             |
                        |  - users                |
                        +-------------------------+

+--------------------------------------------------+
|  Browser (3 independent pages)                    |
|  +---------------+ +-------------+ +-----------+  |
|  | dashboard.html| | calendar.html| | index.html| |
|  | dashboard.js  | | calendar.js | | home.js   |  |
|  | dashboard.css | | calendar.css| | home.css  |  |
|  | (1457 LOC)    | | (583 LOC)   | | (253 LOC) |  |
|  +---------------+ +-------------+ +-----------+  |
+--------------------------------------------------+

+--------------------------------------------------+
|  stats-dashboard/ (NOT CONNECTED - React proto)  |
|  Vite + React 19 + Tailwind - standalone SPA     |
+--------------------------------------------------+
```

## Data Flow

### Scraper Flow (Background Thread)

1. `background_updater()` in `app.py:258-262` runs in a daemon thread, loops forever with 180s sleep
2. Calls `fetch_entries_data()` in `app.py:183-255` each iteration
3. `get_gym_session()` in `app.py:127-168` manages a `requests.Session` to the eFitness portal, authenticating with GYM_EMAIL/GYM_PASSWORD via form POST
4. Scrapes HTML from the gym's member portal page, parses with BeautifulSoup to find regex pattern `Aktualnie w klubie (\d+) / \d+`
5. Updates the global `entries_cache` dict in-memory (`app.py:115-120`)
6. Calls `save_to_firestore()` in `app.py:171-180` which writes to both `daily_entries` and `hourly_occupancy` Firestore collections

### API Request Flow (Authenticated Endpoints)

1. Client JS calls `/api/workouts/*` or `/api/analytics/*` with `credentials: 'same-origin'`
2. Flask session cookie (server-side, `PERMANENT_SESSION_LIFETIME=365 days`) identifies user
3. `require_login()` in `app.py:82-87` extracts `user_id` from `session['user_id']`; returns 401 if missing
4. Route handler calls corresponding `database.py` function with `user_id` parameter
5. `database.py` queries Firestore, filters documents by `user_id` field
6. JSON response returned to client

### Authentication Flow

1. User submits username/password via `dashboard.js` login overlay
2. POST to `/api/auth/login` in `app.py:672-695`
3. `database.authenticate_user()` in `database.py:214-244` does case-insensitive username lookup in `users` collection, verifies bcrypt hash
4. On success: `session['user_id']` and `session['username']` set in Flask server-side session; session cookie sent to browser
5. Client stores username in `localStorage` as display cache only (auth is server-side)
6. `authFetch()` wrapper in `dashboard.js:64-73` catches 401 responses and triggers re-login overlay

### Occupancy Analytics Flow (Public Endpoints)

1. Background scraper accumulates hourly data into `hourly_occupancy` collection (doc ID: `YYYY-MM-DD-HH`)
2. `/api/analytics/extended` calls `get_extended_occupancy_stats()` in `database.py:1569-1602`
3. This function calls `fetch_recent_hourly_data(30)` once, then passes `cached_data` to all sub-functions (daily averages, hourly averages, best/worst combos) to avoid N+1 Firestore queries
4. `is_complete_day()` in `database.py:66-120` filters out holidays/early closures by detecting 4+ consecutive zeros or identical trailing values

**State Management (Frontend):**
- Global JS variables per page (no framework state management)
- `dashboard.js` maintains: `currentYear`, `currentMonth`, `selectedDate`, `selectedParts`, `weightData`, `workoutsData`, `bodyPartsConfig`, `heatmapYear`, `completenessData`, `currentUser`
- Client-side cache with 60s TTL: `statsCache`, `newYearCache` in `dashboard.js:33-35`
- `calendar.js` duplicates similar state: `currentYear`, `currentMonth`, `selectedDate`, `selectedParts`, `workoutsData`, `bodyPartsConfig`

## Module Boundaries

### `app.py` (1012 LOC) - Flask Server

- **Purpose:** HTTP routing, request handling, scraping, security
- **Location:** `app.py` (project root)
- **Contains:**
  - Scraper logic (session management, HTML parsing, background thread)
  - All API route handlers (~40 endpoints)
  - Auth middleware (`get_current_user_id`, `require_login`)
  - Security (CSP, CORS, rate limiting, HTTPS enforcement)
  - Admin secret-gated endpoints
- **Depends on:** `database` module, Flask, requests, BeautifulSoup
- **Used by:** All frontend pages via HTTP API

### `database.py` (2060 LOC) - Firestore Data Layer

- **Purpose:** All database read/write operations, business logic, analytics calculations
- **Location:** `database.py` (project root)
- **Contains:**
  - User authentication (create, authenticate, bcrypt hashing)
  - Workout CRUD (save, get, delete, monthly queries)
  - Dashboard stats aggregation
  - Hourly occupancy tracking and analysis
  - Extended analytics (daily averages, hourly averages, best/worst combos, new year effect)
  - Data quality checks (`is_complete_day`, `is_gym_open`)
  - Export/backup functions
  - Personal records and progression tracking
  - Configuration constants (`BODY_PARTS`, `GYM_HOURS`)
- **Depends on:** `google.cloud.firestore`, `bcrypt`, `pytz`
- **Used by:** `app.py` exclusively

### `static/js/dashboard.js` (1457 LOC) - Main Dashboard Client

- **Purpose:** Complete client-side logic for the main dashboard page
- **Location:** `static/js/dashboard.js`
- **Contains:**
  - Authentication UI (login/register overlay, session check)
  - Calendar rendering and workout modal (create/edit/delete)
  - Live occupancy counter (60s polling)
  - Statistics tab (daily chart, hourly chart, best/worst times, new year effect)
  - Strength tab (personal records, progression SVG charts)
  - Heatmap rendering (yearly workout view)
  - Month comparison
  - Export/backup download
- **Depends on:** DOMPurify (bundled as `purify.min.js`), REST API endpoints
- **Used by:** `templates/dashboard.html`

### `static/js/calendar.js` (583 LOC) - Standalone Calendar

- **Purpose:** Calendar-only page with workout tracking
- **Location:** `static/js/calendar.js`
- **Contains:** Duplicate calendar/workout logic from dashboard.js (no shared code)
- **Depends on:** REST API endpoints
- **Used by:** `templates/calendar.html`

### `static/js/home.js` (253 LOC) - Legacy Home Page

- **Purpose:** Simple occupancy display with manual refresh
- **Location:** `static/js/home.js`
- **Contains:** Occupancy fetch, stats display, refresh button with cooldown
- **Depends on:** REST API endpoints `/api/occupancy`, `/api/stats`, `/api/refresh`
- **Used by:** `templates/index.html`

## Key Abstractions

### Workout Document

- **Purpose:** Represents a single workout session for a user on a date
- **Examples:** `database.py:435-469` (`save_workout`), `database.py:481-495` (`get_workout`)
- **Pattern:** Firestore document with composite ID `{user_id}_{date_str}`
- **Schema:** `{date, user_id, body_parts: [str], weight_data: {part: {kg, sets, reps}}, notes, created_at}`

### Hourly Occupancy Document

- **Purpose:** Single hourly occupancy reading from the gym
- **Examples:** `database.py:854-889` (`save_hourly_occupancy`)
- **Pattern:** Firestore document with ID `YYYY-MM-DD-HH`, deduplicated per hour
- **Schema:** `{date, hour, weekday, occupancy, timestamp}`

### Body Parts Config

- **Purpose:** Defines available muscle groups with display metadata
- **Examples:** `database.py:395-404` (`BODY_PARTS` dict)
- **Pattern:** Static dict shared between backend responses and frontend rendering
- **Keys:** `lydki`, `uda`, `brzuch`, `biceps`, `triceps`, `barki`, `plecy`, `klata`

### User Document

- **Purpose:** Registered user with bcrypt-hashed password
- **Examples:** `database.py:171-211` (`create_user`)
- **Pattern:** Firestore document with UUID `user_id`, case-insensitive username via `username_lower`
- **Schema:** `{user_id, username, username_lower, password_hash, created_at}`

## Entry Points

### Application Server

- **Location:** `app.py:1002-1009`
- **Triggers:** `python app.py` (dev) or `gunicorn app:app` (production via Dockerfile)
- **Responsibilities:** Starts Flask server, kicks off initial data fetch, starts background scraper thread

### Dashboard Page

- **Location:** `static/js/dashboard.js:1457` calls `init()` -> `dashboard.js:242-246`
- **Triggers:** Browser loads `templates/dashboard.html` via `GET /`
- **Responsibilities:** Checks auth, shows login overlay or starts app (fetches live count, dashboard stats, month workouts, completeness data)

### Calendar Page

- **Location:** `static/js/calendar.js:23-28` (`init()`)
- **Triggers:** Browser loads `templates/calendar.html` via `GET /calendar`
- **Responsibilities:** Fetches dashboard data and month workouts, renders calendar

### Legacy Page

- **Location:** `static/js/home.js:53-60` (`fetchData()`)
- **Triggers:** Browser loads `templates/index.html` via `GET /legacy`
- **Responsibilities:** Fetches occupancy data and stats, sets up auto-refresh

## Error Handling

**Strategy:** Try/catch at route handler level; log to stdout; return JSON error to client

**Patterns:**
- Every route handler in `app.py` wraps database calls in try/except, returns `{'error': str(e)}` with 500 status
- Firestore unavailability returns 503: `{'error': 'Firestore not available'}`
- Auth failures return 401: `{'error': 'Not authenticated'}` or `{'success': False, 'error': '...'}`
- Scraper failures update `entries_cache['status']` to `'error'` with Polish error messages
- Frontend `authFetch()` wrapper in `dashboard.js:64-73` catches 401 globally and forces re-login
- Rate limit violations handled per-endpoint by flask-limiter; client-side also caches with 60s TTL

## Cross-Cutting Concerns

**Logging:**
- Backend uses `print()` statements throughout `app.py` for scraper status
- `database.py` uses `logging.getLogger(__name__)` for data fetch performance (`logger.info`, `logger.error`)
- No structured logging or log levels configured on `app.py`

**Validation:**
- Input validation in route handlers (date format regex, body part whitelist)
- Username/password validation in `database.py:127-154` (length 3-20, alphanumeric username)
- Admin endpoints protected by timing-safe `secrets.compare_digest()` against `ADMIN_SECRET` env var

**Authentication:**
- Server-side Flask sessions with 365-day lifetime
- Session cookie: `Secure`, `HttpOnly`, `SameSite=Lax`
- Admin endpoints use separate `X-Admin-Secret` header (not session-based)
- No RBAC -- all authenticated users have equal access to their own data
- Occupancy/stats endpoints are public (no auth required)

**Timezone:**
- All datetime operations use `Europe/Warsaw` timezone via `pytz`
- Consistent across scraper, database writes, and analytics calculations

---

*Architecture analysis: 2026-04-04*
