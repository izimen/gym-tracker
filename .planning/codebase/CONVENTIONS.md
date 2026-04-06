# Coding Conventions

**Analysis Date:** 2026-04-04

## Naming Conventions

### Python (Backend)

**Files:**
- `snake_case.py` for all modules: `app.py`, `database.py`
- Single-file architecture (no package splitting)

**Functions:**
- Use `snake_case` for all functions
- Route handlers named after their purpose: `save_workout()`, `get_entries()`, `delete_workout()`
- Internal helpers prefixed descriptively: `get_current_user_id()`, `require_login()`, `fetch_entries_data()`
- Database functions match the CRUD operation: `save_workout()`, `get_workout()`, `delete_workout()`
- Analytics functions use `get_` prefix: `get_hourly_averages()`, `get_daily_averages()`

**Variables:**
- `snake_case` throughout: `entries_cache`, `current_session`, `session_lock`
- Constants use `UPPER_SNAKE_CASE`: `FIRESTORE_ENABLED`, `REQUEST_TIMEOUT`, `REFRESH_COOLDOWN`, `GYM_HOURS`, `BODY_PARTS`, `DEFAULT_USER_ID`
- Prefixed underscores for module-private: `_secret_key`, `_secret_file`

**Type Hints:**
- `database.py` uses type hints extensively on all public functions:
  ```python
  def get_week_ago_entries() -> Optional[dict]:
  def get_average_for_weekday(weekday: Optional[int] = None) -> float:
  def save_workout(date_str: str, body_parts: list, weight_data: Optional[dict] = None, notes: Optional[str] = None, user_id: Optional[str] = None):
  ```
- `app.py` does NOT use type hints on route handlers or helper functions (except `save_to_firestore(entries_count: int)`)
- Imports from `typing`: `List`, `Dict`, `Any`, `Optional` (in `database.py`)

**Prescriptive rule:** Add return type annotations to all new Python functions. Use `Optional[T]` for nullable params. Match `database.py` style.

### JavaScript (Frontend)

**Functions:**
- `camelCase` for all functions: `fetchDashboard()`, `renderCalendar()`, `openModal()`, `closeModal()`
- Fetch functions prefixed with `fetch`: `fetchLiveCount()`, `fetchExtendedStats()`, `fetchWeeklyChart()`
- Render functions prefixed with `render`: `renderCalendar()`, `renderHeatmap()`, `renderComparison()`
- Event handlers named for their action: `handleLogin()`, `handleRegister()`, `saveWorkout()`, `deleteWorkout()`

**Variables:**
- `camelCase` for local/module variables: `currentYear`, `selectedParts`, `workoutsData`, `bodyPartsConfig`
- `UPPER_SNAKE_CASE` for constants: `MONTHS_PL`, `CACHE_TTL`, `REFRESH_COOLDOWN_MS`

**Prescriptive rule:** Use `camelCase` for all JS functions and variables. Prefix async data fetchers with `fetch`, rendering functions with `render`.

### HTML/CSS

**IDs:**
- `camelCase` for element IDs: `calendarDays`, `weeklyCount`, `modalOverlay`, `bodyPartsGrid`
- Exceptions: `deleteBtn`, `loginForm`, `registerForm`

**CSS Classes:**
- `kebab-case` for CSS classes: `legend-item`, `body-part-btn`, `chart-bar-wrapper`, `data-complete`

**Prescriptive rule:** Use `camelCase` for HTML IDs, `kebab-case` for CSS classes.

## Code Style & Formatting

### Formatting Tools

- **No linter configured** (no `.eslintrc`, `.prettierrc`, `pyproject.toml [tool.ruff]`, etc.)
- **Pre-commit hooks** (`.pre-commit-config.yaml`):
  - `trailing-whitespace` fixer
  - `end-of-file-fixer`
  - `check-yaml`
  - `check-added-large-files`
  - `gitleaks` secret scanning (v8.18.1)

**Prescriptive rule:** No auto-formatting is enforced. Use 4-space indentation for Python, 4-space for JS. Follow existing patterns.

### Python Indentation & Structure

- 4-space indentation throughout
- Section headers use banner comments in both files:
  ```python
  # =============================================================================
  # WORKOUT CALENDAR API ENDPOINTS
  # =============================================================================
  ```
- Logical grouping within `app.py`:
  1. Imports and initialization
  2. Session/auth helpers
  3. Config constants
  4. Scraping logic
  5. Route handlers grouped by feature (occupancy, workouts, analytics, auth, admin, export)
  6. Security headers (at bottom as `@app.after_request`)

### JavaScript Indentation & Structure

- 4-space indentation throughout
- Section headers use comment blocks:
  ```javascript
  // ============================================
  // AUTHENTICATION
  // ============================================
  ```
- `dashboard.js` sections: Utils, State, Tab Switching, Authentication, Initialization, Live Counter, Dashboard Data, Calendar, Modal, Statistics, Export, Strength Tab, Start
- `calendar.js` is simpler: flat organization without section headers
- `home.js` uses `DOMContentLoaded` event listener pattern for initialization

### Import Organization (Python)

`app.py` import order:
1. Standard library (`os`, `secrets`, `datetime`, `threading`, `time`, `re`)
2. Third-party (`flask`, `flask_cors`, `requests`, `bs4`, `pytz`)
3. Local (`database`)
4. Late imports inside function body (`flask_limiter`, `flask_compress` at module level but after `app` creation)

`database.py` import order:
1. Third-party (`google.cloud.firestore`, `bcrypt`)
2. Standard library (`datetime`, `pytz`, `re`, `uuid`, `os`, `secrets`, `logging`, `time`)
3. Type hints (`typing`)

**Prescriptive rule:** Group imports as stdlib, third-party, local. `database.py` breaks this convention -- new code should follow stdlib-first order.

## Documentation Patterns

### Python Docstrings

**`database.py` -- thorough documentation:**
- Every public function has a docstring
- Docstrings describe purpose, parameters, and return types:
  ```python
  def is_gym_open(weekday: int, hour: int) -> bool:
      """
      Check if gym is open at given weekday and hour.
      
      Args:
          weekday: 0=Monday, 6=Sunday
          hour: 0-23 (represents the start of the hour slot)
      
      Returns:
          True if gym is open, False otherwise
      """
  ```
- Customization sections include inline comments explaining format:
  ```python
  # CUSTOMIZATION: Modify BODY_PARTS to customize workout categories.
  # Each entry: 'key': {'name': 'Display Name', 'emoji': '', 'color': '#HEX'}
  ```
- Collection names and document ID formats are documented:
  ```python
  """
  Save a workout for a specific date.
  Collection: workouts
  Document ID: {user_id}_{date} for per-user storage
  """
  ```

**`app.py` -- minimal documentation:**
- Route handlers have single-line docstrings: `"""Serve the main dashboard"""`
- Helper functions have brief docstrings: `"""Get user_id from server-side session. Returns None if not logged in."""`
- No Args/Returns format used

**Prescriptive rule:** Follow `database.py` style for new functions: include Args, Returns sections. Use `database.py`'s Collection/Document ID pattern when adding Firestore functions.

### JavaScript Comments

- No JSDoc used anywhere
- Inline comments for non-obvious logic:
  ```javascript
  // Monday = 0, Sunday = 6 (adjusted from JS's Sunday = 0)
  let startDay = firstDay.getDay() - 1;
  ```
- `// Auth is now handled via server-side session cookies` -- migration notes

**Prescriptive rule:** No JSDoc required. Use inline comments for business logic. Section headers for major sections.

### Changelog

- `zmiany.md` -- written in Polish, documents security changes and frontend refactoring
- Not actively maintained (last entry about CSP refactoring tasks marked "Do realizacji teraz")

## Error Handling Patterns

### Python Backend

**Route handler pattern (consistent across all endpoints):**
```python
@app.route('/api/workout/<date_str>', methods=['GET'])
def get_workout(date_str):
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id, err = require_login()
    if err:
        return err
    
    try:
        workout = database.get_workout(date_str, user_id)
        return jsonify(workout or {})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Pattern breakdown:**
1. Check `FIRESTORE_ENABLED` first (503 if disabled)
2. Call `require_login()` which returns `(user_id, None)` or `(None, error_response)`
3. Wrap business logic in `try/except Exception`
4. Return `{'error': str(e)}` with 500 on failure

**Admin endpoints add secret verification:**
```python
secret = request.headers.get('X-Admin-Secret') or request.args.get('secret') or ''
if not ADMIN_SECRET or not secrets.compare_digest(secret, ADMIN_SECRET):
    return jsonify({'error': 'Unauthorized'}), 401
```

**Prescriptive rule:** Follow this exact pattern for all new route handlers. Always check FIRESTORE_ENABLED, then require_login, then try/except.

### JavaScript Frontend

**Fetch error handling pattern:**
```javascript
async function fetchDashboard() {
    try {
        const response = await authFetch('/api/workouts/dashboard');
        const data = await response.json();
        // ... update DOM
    } catch (error) {
        console.error('Error fetching dashboard:', error);
    }
}
```

**User-facing errors use `alert()`:**
```javascript
if (!response.ok) {
    const data = await response.json();
    alert('Error: ' + (data.error || 'Unknown error'));
}
```

**Session-expired handling via `authFetch()` wrapper in `dashboard.js`:**
```javascript
async function authFetch(url, options = {}) {
    if (!options.credentials) options.credentials = 'same-origin';
    const res = await fetch(url, options);
    if (res.status === 401) {
        clearUser();
        showLoginOverlay();
        throw new Error('Session expired');
    }
    return res;
}
```

**Rate limiting handling:**
```javascript
if (response.status === 429) {
    console.warn('Rate limited, skipping...');
    return;
}
```

**Prescriptive rule:** Use `authFetch()` for all authenticated API calls in `dashboard.js`. Use plain `fetch()` only for public endpoints. Log errors with `console.error()`. Show user-facing errors via `alert()`.

## Security Patterns

### XSS Prevention

**DOMPurify sanitization wrapper (in all JS files):**
```javascript
function safeSanitize(html) {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(html);
    }
    console.warn('DOMPurify not loaded, falling back to raw HTML');
    return html;
}
```
Used for any `innerHTML` that includes dynamic data. Present in `dashboard.js`, `calendar.js`, `home.js`.

**Prescriptive rule:** Always wrap `innerHTML` assignments containing server data through `safeSanitize()`. Never insert unsanitized user content.

### Authentication

- Server-side session via Flask: `session['user_id']`
- `get_current_user_id()` reads from session only (never from request body/params)
- `require_login()` returns tuple: `(user_id, None)` or `(None, (jsonify_error, 401))`
- Cookie flags: `HTTPONLY=True`, `SAMESITE='Lax'`, `SECURE=True`

### Admin Protection

- Uses `secrets.compare_digest()` for timing-safe comparison
- Admin secret read from `X-Admin-Secret` header or `secret` query param
- Pattern repeated identically across all admin endpoints in `app.py` (lines 722, 749, 771, 793, 868, 897)

**Prescriptive rule:** For new admin endpoints, copy the exact admin secret check pattern. Never use `==` for secret comparison.

### Input Validation

- Date format validated via regex: `re.match(r'^\d{4}-\d{2}-\d{2}$', date_str)`
- Body parts validated against `database.BODY_PARTS.keys()`
- Username: alphanumeric, 3-20 chars via regex `r'^[a-zA-Z0-9]+$'`
- Password: 3-20 chars length check only (no complexity requirements)

### Security Headers

Unified in `add_security_headers()` at `app.py` lines 963-999:
- CSP with `unsafe-inline` still present (script-src, style-src)
- HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- Permissions-Policy blocking geolocation/microphone/camera
- CORS restricted to allowed origins via env var

## Logging

### Python

**Inconsistent approach between files:**

- `app.py` uses `print()` for all logging (21 print statements, 2 `app.logger.error()` calls in export endpoints)
- `database.py` uses proper `logging` module:
  ```python
  logger = logging.getLogger(__name__)
  logger.info(f"Fetched {len(data)} hourly records in {duration:.3f}s")
  logger.warning("ADMIN_PASSWORD env var not set")
  logger.error(f"Error fetching hourly data: {e}")
  ```
  But also has a `print("Created admin user.")` on line 432

**Prescriptive rule:** Use `logging` module for all new code. In `app.py`, use `app.logger` (Flask's built-in logger). In `database.py`, use the existing `logger = logging.getLogger(__name__)`. Do not use `print()`.

### JavaScript

- `console.error()` for caught errors
- `console.warn()` for rate limiting and fallback situations
- `console.log()` for cache status messages
- No structured logging framework

## Language

- UI text is in **Polish** (Polskie nazwy): button labels, error messages, alerts
- Code identifiers are in **English**: function names, variable names, API routes
- Exception: `BODY_PARTS` keys use Polish (`klata`, `plecy`, `biceps`, `barki`, `lydki`, `uda`, `brzuch`, `triceps`)
- Polish month names defined as constants: `MONTHS_PL` in JS, inline lists in Python

**Prescriptive rule:** Keep all code identifiers in English. Keep all user-facing strings in Polish. Body part keys remain in Polish for backward compatibility.

---

*Convention analysis: 2026-04-04*
