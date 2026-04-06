# Technical Concerns & Risks

**Analysis Date:** 2026-04-04  
**Last Updated:** 2026-04-06

---

> **ETAP 2 Update (2026-04-06):** The following concerns have been FIXED:
> - **C-01** (.dockerignore) — FIXED
> - **C-02** (password policy) — FIXED (min 8, max 128, complexity)
> - **C-03** (debug endpoint auth) — FIXED (admin secret required)
> - **H-01** (user enumeration) — FIXED (generic message + dummy bcrypt)
> - **H-02** (admin secret in query) — FIXED (header only)
> - **H-03** (DOMPurify fallback) — FIXED (textContent escape)
> - **H-07** (GET for destructive op) — FIXED (changed to DELETE)
> - **M-01** (missing rate limits) — FIXED (15 endpoints)
> - **M-06** (exception messages) — FIXED (generic errors + server-side logging)
>
> **Still open:** H-04 (CSRF), H-05 (account lockout), H-06 (thread safety), M-02 (Firestore queries), M-03 (CSP unsafe-inline), M-05 (CI/CD env vars), all Low/TD items.

---

## Critical (Must Fix Before Production)

### C-01: .dockerignore Missing .env -- Credentials Leak to Docker Image — FIXED

- **Location:** `.dockerignore` (full file, 13 lines)
- **Evidence:** The `.dockerignore` file lists `Dockerfile`, `README.md`, `*.pyc`, `venv`, `.git`, etc. but does NOT list `.env`, `.env.*`, or any environment files. Meanwhile, `Dockerfile:11` runs `COPY . ./` which copies everything not excluded.
- **Impact:** If `.env` exists on the build machine (and it does -- confirmed present on disk), it gets baked into the Docker image layer. Anyone with image pull access can extract all credentials (GYM_EMAIL, GYM_PASSWORD, ADMIN_SECRET, SECRET_KEY, etc.). This is a **credential leak** to the container registry.
- **Remediation:** Add these lines to `.dockerignore`:
  ```
  .env
  .env.*
  .env.local
  .env.production
  ```
  Note: `.gitignore` already excludes `.env` from git (lines 2-5), but `.dockerignore` is a completely separate mechanism.

### C-02: Password Policy Allows 3-Character Passwords

- **Location:** `database.py:143-154` (`validate_password` function)
- **Evidence:**
  ```python
  def validate_password(password: str) -> tuple:
      if not password:
          return False, "Password is required"
      if len(password) < 3:
          return False, "Password must be at least 3 characters"
      if len(password) > 20:
          return False, "Password must be at most 20 characters"
      return True, None
  ```
- **Impact:** 3-character passwords are trivially brute-forceable even with bcrypt. No complexity requirements (uppercase, digits, symbols) exist. Combined with no account lockout (see C-03), an attacker can enumerate weak passwords quickly. The max length of 20 is also unnecessarily restrictive since bcrypt can handle longer passwords.
- **Remediation:** Increase minimum to 8 characters. Add complexity requirement (at least one digit and one letter). Remove or raise the max-length cap (bcrypt truncates at 72 bytes, so cap at 72 if needed). Example:
  ```python
  if len(password) < 8:
      return False, "Password must be at least 8 characters"
  if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
      return False, "Password must contain at least one letter and one digit"
  ```

### C-03: Debug Endpoint Exposes Firestore Data Without Authentication

- **Location:** `app.py:592-639` (`debug_day_data` function)
- **Evidence:**
  ```python
  @app.route('/api/debug/day/<date_str>')
  def debug_day_data(date_str):
      """Debug endpoint to check raw hourly data for a specific day"""
      # ... no auth check, no admin secret check ...
      db = database.get_db()
  ```
  This endpoint has NO authentication, NO admin secret check, and NO rate limiting. It returns raw Firestore hourly occupancy data for any date.
- **Impact:** Any unauthenticated user can query raw gym occupancy data for any day. While this is "debug" data, it exposes internal database structure and bypasses all access controls. An attacker can scrape the entire hourly_occupancy collection day by day.
- **Remediation:** Either delete this endpoint entirely (it is a debug tool) or protect it with the same admin secret check used by other admin endpoints:
  ```python
  secret = request.headers.get('X-Admin-Secret') or request.args.get('secret') or ''
  if not ADMIN_SECRET or not secrets.compare_digest(secret, ADMIN_SECRET):
      return jsonify({'error': 'Unauthorized'}), 401
  ```

---

## High Priority

### H-01: User Enumeration via Differentiated Error Messages

- **Location:** `database.py:233-238` (`authenticate_user` function)
- **Evidence:**
  ```python
  if not user_doc:
      return {'success': False, 'error': 'User not found'}

  if not verify_password(password, user_doc.get('password_hash', '')):
      return {'success': False, 'error': 'Wrong password'}
  ```
- **Impact:** An attacker can determine whether a username exists by checking the error message. "User not found" vs "Wrong password" allows enumerating valid accounts before attempting password attacks.
- **Remediation:** Return a single generic error for both cases:
  ```python
  return {'success': False, 'error': 'Invalid username or password'}
  ```
  Also ensure bcrypt comparison runs even when user is not found (to prevent timing attacks):
  ```python
  if not user_doc:
      verify_password(password, "$2b$12$dummy_hash_to_prevent_timing")
      return {'success': False, 'error': 'Invalid username or password'}
  ```

### H-02: Admin Secret Accepted via Query String -- Logged in URLs

- **Location:** `app.py:722,749,771,792,868,893` (six admin endpoints)
- **Evidence:**
  ```python
  secret = request.headers.get('X-Admin-Secret') or request.args.get('secret') or ''
  ```
  All admin endpoints accept the secret via `request.args.get('secret')`, meaning the admin secret can be passed as `?secret=VALUE` in the URL.
- **Impact:** Query parameters are logged in web server access logs, browser history, proxy logs, CDN logs, and Cloud Run request logs. The admin secret leaks to all these locations. The secret grants access to password resets, user listing, data export, and destructive data deletion.
- **Remediation:** Remove `request.args.get('secret')` from all admin endpoints. Accept the secret only via the `X-Admin-Secret` header:
  ```python
  secret = request.headers.get('X-Admin-Secret', '')
  ```

### H-03: DOMPurify Fallback Returns Raw HTML -- XSS Risk

- **Location:** `static/js/dashboard.js:6-12` and `templates/index.html:613-619`
- **Evidence:**
  ```javascript
  function safeSanitize(html) {
      if (typeof DOMPurify !== 'undefined') {
          return DOMPurify.sanitize(html);
      }
      console.warn('DOMPurify not loaded, falling back to raw HTML');
      return html;  // unsanitized HTML returned
  }
  ```
  The function is defined identically in both files. If `purify.min.js` fails to load (CDN outage, network error, ad blocker), the fallback passes raw HTML through to DOM element content assignments.
- **Impact:** If DOMPurify fails to load, every call to `safeSanitize()` becomes a no-op, and all dynamic content assignments using its result become potential XSS vectors. While most data comes from the server, any user-controlled data (workout notes, body part names via config manipulation) would be injectable.
- **Remediation:** Fail closed -- strip all HTML tags if DOMPurify is unavailable:
  ```javascript
  function safeSanitize(html) {
      if (typeof DOMPurify !== 'undefined') {
          return DOMPurify.sanitize(html);
      }
      console.warn('DOMPurify not loaded, stripping all HTML');
      const div = document.createElement('div');
      div.textContent = html;
      return div.textContent;
  }
  ```

### H-04: No CSRF Token Protection

- **Location:** All POST endpoints in `app.py` (lines 367, 646, 672, 698, 714)
- **Evidence:** No POST endpoint checks for a CSRF token. The only CSRF protection is `SESSION_COOKIE_SAMESITE = 'Lax'` (line 52). There is no Flask-WTF or manual CSRF token generation anywhere in the codebase.
- **Impact:** SameSite=Lax protects against cross-site POST attacks in modern browsers, but does NOT protect against: same-site attacks (subdomain-based), older browsers without SameSite support, or attacks where the attacker has a page on the same registrable domain. Endpoints at risk: workout creation/deletion, user registration, password reset.
- **Remediation:** Install `flask-wtf` and enable CSRF protection globally, or implement manual CSRF tokens. For a JSON API, validating a custom header (e.g., `X-Requested-With`) on all state-changing requests is a lighter alternative.

### H-05: No Account Lockout After Failed Login Attempts

- **Location:** `app.py:672-695` (login endpoint) and `database.py:214-244` (authenticate_user)
- **Evidence:** The login endpoint has `@limiter.limit("10 per minute")` but no tracking of failed attempts per account. An attacker can try 10 passwords per minute per IP indefinitely. With multiple IPs (botnets, proxies), the rate limit is easily bypassed.
- **Impact:** Combined with the 3-character password policy (C-02), brute-force attacks are highly feasible. 10 attempts/minute = 600/hour = 14,400/day per IP.
- **Remediation:** Track failed login attempts per username in Firestore. Lock the account (or add progressive delays) after 5 consecutive failures. Require a cooldown period or CAPTCHA to unlock.

### H-06: Thread Safety Issue on entries_cache Dict

- **Location:** `app.py:115-120` (cache definition) and `app.py:183-255` (fetch_entries_data modifies it)
- **Evidence:**
  ```python
  entries_cache = {
      'entries_today': 0,
      'last_updated': None,
      'status': 'initializing',
      'error': None
  }
  ```
  This dict is read by request handlers (lines 287-289, 296, 301-330) and written by the background updater thread (line 260-262 calls `fetch_entries_data` which mutates `entries_cache`). There is no lock protecting reads/writes to this dict.
- **Impact:** While CPython's GIL makes individual dict operations atomic, multi-key reads (e.g., reading `status` then `entries_today`) can see inconsistent state -- for example, a partially-updated cache where `status` is 'ok' but `entries_today` is stale. With gunicorn's 8 threads (`Dockerfile:21`), this is a real concurrency scenario.
- **Remediation:** Either use a threading.Lock around all reads/writes to `entries_cache`, or replace the mutable dict with an immutable snapshot pattern:
  ```python
  # Write: replace entire dict atomically
  entries_cache = {
      'entries_today': entries_today,
      'last_updated': ...,
      'status': 'ok',
      'error': None
  }
  # Read: capture reference once
  cache = entries_cache  # atomic reference copy
  return jsonify(cache)
  ```

### H-07: Destructive Admin Endpoint Uses GET Method

- **Location:** `app.py:764-783` (`reset_hourly_data`)
- **Evidence:**
  ```python
  @app.route('/api/admin/reset-hourly')
  def reset_hourly_data():
      """Reset hourly occupancy data - clears all records to start fresh"""
  ```
  This endpoint uses the default GET method but performs a destructive action (deleting all hourly occupancy records from Firestore via `database.clear_hourly_occupancy()`).
- **Impact:** GET requests can be triggered by browser prefetching, search engine crawlers, link previews, or cached proxy replays. An accidental click or bookmark could wipe all hourly data. Combined with the admin secret in query string (H-02), a logged URL could be replayed.
- **Remediation:** Change to POST or DELETE method:
  ```python
  @app.route('/api/admin/reset-hourly', methods=['POST'])
  ```

---

## Medium Priority

### M-01: Many Analytics Endpoints Lack Rate Limiting

- **Location:** `app.py` -- the following endpoints have NO `@limiter.limit()` decorator:
  - Line 367: `/api/workout` (POST)
  - Line 404: `/api/workout/<date_str>` (GET)
  - Line 421: `/api/workout/<date_str>` (DELETE)
  - Line 438: `/api/workouts/month/<int:year>/<int:month>`
  - Line 460: `/api/workouts/dashboard`
  - Line 482: `/api/analytics/weekly`
  - Line 499: `/api/analytics/heatmap/<int:year>`
  - Line 516: `/api/analytics/comparison`
  - Line 533: `/api/analytics/best-hours`
  - Line 575: `/api/analytics/completeness/<int:year>/<int:month>`
  - Line 592: `/api/debug/day/<date_str>`
  - Line 907: `/api/strength`
  - Line 924: `/api/progression/<part>`
- **Impact:** These endpoints still have the default global limit of "1000 per day, 150 per hour" (`app.py:67`), but many of them trigger expensive Firestore queries (full collection scans). An attacker could DoS the Firestore quota or generate significant cloud billing by hitting these endpoints rapidly.
- **Remediation:** Add explicit rate limits to Firestore-heavy endpoints. Recommended: `@limiter.limit("30 per minute")` for analytics endpoints, `@limiter.limit("60 per minute")` for workout CRUD endpoints.

### M-02: Firestore Queries Fetch All Users' Data Then Filter Client-Side

- **Location:** `database.py:512-525` (`get_month_workouts`)
- **Evidence:**
  ```python
  docs = db.collection('workouts')\
      .where('date', '>=', start_date)\
      .where('date', '<', end_date)\
      .stream()

  workouts = []
  for doc in docs:
      data = doc.to_dict()
      doc_user_id = data.get('user_id', DEFAULT_USER_ID)
      if doc_user_id == user_id:
          workouts.append(data)
  ```
  The Firestore query fetches ALL users' workouts for the month, then filters by `user_id` in Python. This pattern repeats in `get_weekly_workout_count` (line 570-581), `get_last_workout` (line 663-674), and `get_weekly_workout_history` (line 723-733).
- **Impact:** As users grow, each query fetches and transfers data for all users unnecessarily. This wastes Firestore read operations (billed per document read) and increases response time. With N users and M workouts each, one request reads N*M documents instead of M.
- **Remediation:** Add a `.where('user_id', '==', user_id)` clause to the Firestore query. Note: Firestore may require a composite index on `(user_id, date)`. Create the index and update queries:
  ```python
  docs = db.collection('workouts')\
      .where('user_id', '==', user_id)\
      .where('date', '>=', start_date)\
      .where('date', '<', end_date)\
      .stream()
  ```

### M-03: CSP Allows unsafe-inline for Scripts and Styles

- **Location:** `app.py:978-988` (Content Security Policy header)
- **Evidence:**
  ```python
  csp = (
      "default-src 'self'; "
      "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
      ...
  )
  ```
- **Impact:** `'unsafe-inline'` in `script-src` defeats most of CSP's XSS protection. This is required because `templates/index.html` contains a large inline `<script>` block (lines 611-849) and inline styles are used throughout. However, it means injected inline scripts would execute.
- **Remediation:** Move the inline script in `templates/index.html` to a separate `.js` file (similar to how `dashboard.js` is already external). Then replace `'unsafe-inline'` with a nonce-based policy: `script-src 'self' 'nonce-{random}' https://cdn.jsdelivr.net`. Generate the nonce per-request in `add_security_headers`.

### M-04: Numerous Dynamic Content Assignments Without Sanitization

- **Location:** `static/js/dashboard.js` -- many dynamic DOM content assignments bypass `safeSanitize()`:
  - Line 421: next-month day cells (unsanitized)
  - Line 439-440: legend rendering (unsanitized)
  - Line 832-837: Rate-limit message (static, low risk)
  - Line 988: Daily chart bar (data from API)
  - Line 1059: Hourly chart bar (data from API)
  - Line 1084-1098: Best/worst times (data from API)
  - Line 1139: Weekly chart bar (data from API)
  - Line 1333-1357: Strength records (data from API, includes `record.name`, `record.date`)
  - Line 1451: SVG chart (data from API)
- **Impact:** Most of these use server-controlled data, so XSS risk is low unless the Firestore database is compromised or an API man-in-the-middle occurs. However, inconsistent sanitization makes it easy to introduce vulnerabilities in future changes.
- **Remediation:** Either route ALL dynamic DOM content through `safeSanitize()`, or preferably use `textContent` for data values and `createElement`/`appendChild` for structure. The codebase already uses `safeSanitize()` for calendar cells (line 361, 403) -- extend this pattern everywhere.

### M-05: CI/CD Deploys Only SECRET_KEY -- Missing Other Environment Variables

- **Location:** `.github/workflows/deploy.yml:35-36`
- **Evidence:**
  ```yaml
  env_vars: |
      SECRET_KEY=${{ secrets.SECRET_KEY }}
  ```
  The deployment only sets `SECRET_KEY`. Other required variables (`GYM_EMAIL`, `GYM_PASSWORD`, `ADMIN_SECRET`, `GYM_URL`, `ALLOWED_ORIGINS`, `ADMIN_PASSWORD`) are not set via the CI pipeline.
- **Impact:** If the Cloud Run service is recreated or deployed to a new revision, it will start without gym credentials, admin secret, or CORS configuration. The app will print warnings (`app.py:99-103`) but will run in a degraded state. This is likely managed via Cloud Run console directly, but it creates a fragile deployment that depends on manual configuration.
- **Remediation:** Set all required environment variables via GitHub Secrets and the `env_vars` or `secrets` field in the deploy step. Alternatively, use Google Secret Manager and reference secrets in the Cloud Run service definition.

### M-06: Exception Messages Exposed to Users in API Responses

- **Location:** Multiple endpoints in `app.py`, e.g.:
  - Line 254: `entries_cache['error'] = str(e)`
  - Line 329: `result['error'] = str(e)`
  - Line 401: `return jsonify({'error': str(e)}), 500`
  - Similar pattern at lines 418, 435, 457, 475, 496, 513, 530, 543, 557, 572, 589, 639, 757, 783, 854, 883, 904, 921, 942
- **Impact:** Raw Python exception messages can leak internal file paths, Firestore collection names, query structures, and stack trace fragments to the client. This aids attackers in understanding the system internals.
- **Remediation:** Log the full exception server-side (`app.logger.error(f"...", exc_info=True)`) and return a generic error to the client (`return jsonify({'error': 'Internal server error'}), 500`).

---

## Low Priority

### L-01: Gunicorn Timeout Set to 0 (Infinite)

- **Location:** `Dockerfile:21`
- **Evidence:**
  ```dockerfile
  CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
  ```
- **Impact:** A stuck request (e.g., waiting on Firestore or the gym website) will hold a gunicorn thread indefinitely. With only 8 threads, 8 stuck requests will exhaust all capacity. Cloud Run has its own timeout (default 300s), but a gunicorn timeout of 30-60s would fail faster and free threads.
- **Remediation:** Set `--timeout 60` (or 30) to match the expected worst-case request duration.

### L-02: Rate Limiter Uses In-Memory Storage

- **Location:** `app.py:64-68`
- **Evidence:**
  ```python
  limiter = Limiter(
      get_remote_address,
      app=app,
      default_limits=["1000 per day", "150 per hour"],
      storage_uri="memory://"
  )
  ```
- **Impact:** Rate limit counters reset on every deployment/restart. On Cloud Run with auto-scaling, each container instance has its own counter, so an attacker hitting multiple instances effectively multiplies their allowed rate.
- **Remediation:** For a single-user hobby project, this is acceptable. For production, switch to Redis-backed storage (`storage_uri="redis://..."`) or use Cloud Run's built-in rate limiting.

### L-03: Background Updater Thread Not Gracefully Stopped

- **Location:** `app.py:258-267`
- **Evidence:**
  ```python
  def background_updater():
      while True:
          fetch_entries_data()
          time.sleep(180)

  updater_thread = threading.Thread(target=background_updater, daemon=True)
  updater_thread.start()
  ```
- **Impact:** The daemon thread will be killed abruptly on shutdown, potentially mid-write to `entries_cache`. This is generally fine for daemon threads but could cause partial updates visible to concurrent request handlers.
- **Remediation:** Use a `threading.Event` for graceful shutdown signaling, or accept this as a known limitation for a single-worker deployment.

### L-04: Dependencies Use >= Version Ranges Without Upper Bounds

- **Location:** `requirements.txt` (all 12 dependencies)
- **Evidence:**
  ```
  flask>=3.1.0
  flask-cors>=6.0.0
  ...
  ```
- **Impact:** A future `pip install` could pull a breaking major version bump. For example, `flask>=3.1.0` would accept Flask 4.0 when released, which could introduce incompatibilities.
- **Remediation:** Pin major versions with upper bounds (`flask>=3.1.0,<4.0`) or use a lockfile (`pip freeze > requirements.lock`) for reproducible builds.

### L-05: Export Endpoints Potentially Expose Other Users' Data

- **Location:** `app.py:861-904` (`export_workouts` and `export_full`)
- **Evidence:** Both endpoints call `database.export_all_workouts()` and `database.export_full_backup()` respectively. These functions (names imply) export ALL data, not filtered by user.
- **Impact:** Anyone with the admin secret can export all users' workout data. This is by design for admin backup, but there is no audit trail of who performed the export.
- **Remediation:** Add logging when export endpoints are accessed. Consider whether per-user export is more appropriate for non-admin use cases.

---

## Technical Debt

### TD-01: Duplicated Code Between Templates and Dashboard JS

- **Location:** `templates/index.html:613-619` and `static/js/dashboard.js:6-12`
- **Issue:** The `safeSanitize()` function is identically defined in both files. The `templates/index.html` file also contains a full copy of the calendar rendering logic and fetch functions that partially overlap with `dashboard.js`.
- **Impact:** Bug fixes or security improvements to `safeSanitize()` must be applied in two places. Divergence risk is high.
- **Fix approach:** Extract the inline script from `templates/index.html` into its own JS file (e.g., `static/js/index.js`) and share common utilities via a shared module.

### TD-02: Monolithic app.py (1012 lines) and database.py (2060 lines)

- **Location:** `app.py` (1012 lines), `database.py` (2060 lines), `static/js/dashboard.js` (1457 lines)
- **Issue:** All backend routes are in a single file. All database operations are in a single file. These files mix concerns: auth, analytics, workouts, scraping, admin, export.
- **Impact:** Difficult to navigate, test in isolation, or modify without risk of side effects. High cognitive load for new contributors.
- **Fix approach:** Split into Flask blueprints: `routes/auth.py`, `routes/admin.py`, `routes/analytics.py`, `routes/workouts.py`. Split `database.py` into `db/auth.py`, `db/workouts.py`, `db/analytics.py`, `db/occupancy.py`.

### TD-03: No Automated Tests

- **Location:** Entire codebase -- no test files exist.
- **Issue:** Zero test files. No `pytest.ini`, `conftest.py`, or `tests/` directory. No test dependencies in `requirements.txt`.
- **Impact:** Every change carries regression risk. The existing AUDIT directory suggests this has been identified previously. Security-sensitive code (password validation, auth flow, admin secret checking) has no test coverage.
- **Fix approach:** Start with critical-path tests: auth flow (login, register, session validation), admin secret validation, password policy enforcement, IDOR prevention on workout endpoints.

### TD-04: Firestore Client-Side Filtering Pattern Used Everywhere

- **Location:** `database.py` -- `get_month_workouts` (line 512-525), `get_weekly_workout_count` (line 570-581), `get_last_workout` (line 663-674), `get_weekly_workout_history` (line 723-733)
- **Issue:** All these functions query by date range only, then filter by `user_id` in Python. This is a systemic pattern, not an isolated incident.
- **Impact:** Linear cost growth with user count. Each function reads every user's data for the requested time range. Firestore charges per document read.
- **Fix approach:** Create a composite Firestore index on `(user_id, date)` for the `workouts` collection. Update all queries to include `.where('user_id', '==', user_id)` as the first filter.

---

## Positive Observations (things done well)

### P-01: Secure Session Configuration
- `app.py:50-53` correctly sets `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, and `SESSION_COOKIE_SAMESITE` -- covering the three essential cookie security attributes.

### P-02: Password Hashing with bcrypt
- `database.py:157-168` uses bcrypt with automatic salt generation. Password verification uses `bcrypt.checkpw` correctly.

### P-03: Timing-Safe Admin Secret Comparison
- All admin endpoints use `secrets.compare_digest()` for constant-time comparison of the admin secret, preventing timing attacks.

### P-04: IDOR Prevention on Workout Endpoints
- Workout CRUD endpoints (`app.py:367-475`) all call `require_login()` and pass the session `user_id` to database functions. The database functions use `user_id` in the document ID (`{user_id}_{date}`), preventing one user from accessing another's data.

### P-05: Comprehensive Security Headers
- `app.py:964-998` sets a thorough set of security headers: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, COOP, CORP, and a detailed CSP.

### P-06: HTTPS Enforcement
- `app.py:955-960` redirects HTTP to HTTPS by checking `X-Forwarded-Proto`, appropriate for Cloud Run deployments.

### P-07: Rate Limiting on Auth Endpoints
- Registration is limited to 5/minute (`app.py:647`) and login to 10/minute (`app.py:673`), providing basic brute-force protection.

### P-08: Input Validation on API Endpoints
- Workout save validates date format with regex (`app.py:381`), validates body parts against allowed list (`app.py:392-395`), and username validation enforces alphanumeric-only (`database.py:138`).

---

*Concerns audit: 2026-04-04*
