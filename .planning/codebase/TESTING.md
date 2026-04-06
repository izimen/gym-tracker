# Testing Patterns

**Analysis Date:** 2026-04-04

## Test Framework

**Runner:**
- Python `unittest` (stdlib)
- No pytest configuration or dependencies
- No test runner configured in `requirements.txt`
- Config: None (no `pytest.ini`, `setup.cfg`, `pyproject.toml`)

**Assertion Library:**
- `unittest.TestCase` built-in assertions (`assertEqual`, `assertIn`, `assertNotEqual`, `assertTrue`)

**Run Commands:**
```bash
python -m unittest tests/security_tests.py   # Run security tests (requires running server on port 5000)
```

**No standard test runner, no coverage tool, no watch mode.**

## Test File Organization

**Location:**
- `tests/` directory at project root
- Single file: `tests/security_tests.py` (131 lines)

**Naming:**
- `*_tests.py` pattern (non-standard; pytest convention is `test_*.py`)

**Structure:**
```
tests/
  security_tests.py    # IDOR + security header tests (131 LOC)
```

No `__init__.py` in tests directory. No conftest.py.

## Current Coverage

**Estimated coverage: less than 5%**

| Area | Files | LOC | Tests | Coverage |
|------|-------|-----|-------|----------|
| Backend routes (`app.py`) | 1 | 1012 | 0 unit tests | 0% |
| Database layer (`database.py`) | 1 | 2060 | 0 unit tests | 0% |
| Dashboard JS (`dashboard.js`) | 1 | 1457 | 0 tests | 0% |
| Calendar JS (`calendar.js`) | 1 | 583 | 0 tests | 0% |
| Home JS (`home.js`) | 1 | 253 | 0 tests | 0% |
| Security (IDOR) | - | - | 3 tests | Targeted only |

**What IS tested (3 tests):**
1. `test_security_headers` -- Verifies CSP, HSTS, X-Content-Type-Options headers exist
2. `test_idor_create_workout` -- Attacker cannot create workouts for another user
3. `test_idor_delete_workout` -- Attacker cannot delete another user's workouts

**What is NOT tested:**
- All route handlers (GET, POST, DELETE)
- All database functions (40+ functions in `database.py`)
- Input validation (date format, body parts, username/password)
- Authentication flow (register, login, logout, session management)
- Rate limiting behavior
- Frontend rendering logic
- Analytics calculations
- Data export/backup
- Edge cases (empty data, boundary dates, concurrent access)

## Existing Tests (Inventory)

### `tests/security_tests.py`

**Test class:** `SecurityTests(unittest.TestCase)`

**Setup:**
```python
def setUp(self):
    self.session = requests.Session()
    self._create_user(TEST_USER, TEST_PASS)
    self._create_user(VICTIM_USER, VICTIM_PASS)
    self.victim_id = self._login_get_id(VICTIM_USER, VICTIM_PASS)
    self.attacker_id = self._login_get_id(TEST_USER, TEST_PASS)
```

**Critical characteristics:**
- These are **integration tests**, not unit tests
- Require a **running server** on `http://127.0.0.1:5000`
- Require a **running Firestore** (creates real users)
- Use `requests` library to make HTTP calls
- Hardcoded test credentials: `security_test_user` / `secure_password_123`
- No teardown/cleanup of test data
- Silent exception swallowing in `_create_user()`:
  ```python
  def _create_user(self, username, password):
      try:
          requests.post(f"{BASE_URL}/api/auth/register", json={...})
      except:
          pass
  ```

**Test pattern:**
```python
def test_idor_create_workout(self):
    """
    IDOR TEST: Attacker attempts to create a workout for Victim.
    SECURE BEHAVIOR: Server ignores 'user_id' in payload and uses logged-in user.
    """
    # 1. Login as attacker
    self.session.post(f"{BASE_URL}/api/auth/login", json={...})
    
    # 2. Send payload with victim's user_id
    payload = {
        "date": target_date,
        "body_parts": ["klata"],
        "user_id": self.victim_id  # Should be ignored
    }
    resp = self.session.post(f"{BASE_URL}/api/workout", json=payload)
    
    # 3. Verify victim doesn't have it
    # 4. Verify attacker does have it
```

## Testing Gaps

### Critical Gaps (High Priority)

**1. No unit tests for `database.py`:**
- 40+ functions with zero test coverage
- Complex calculation logic in `get_hourly_averages()`, `get_daily_averages()`, `is_complete_day()`
- Authentication functions (`create_user`, `authenticate_user`, `verify_password`)
- Data integrity functions (`save_workout`, `get_workout`, `delete_workout`)
- Files: `database.py` (all functions)

**2. No unit tests for `app.py` route handlers:**
- 25+ route handlers with zero test coverage
- Input validation not tested (date format, body parts, missing fields)
- Error paths not tested (Firestore unavailable, invalid data)
- Rate limiting not tested
- Admin endpoint authorization not tested
- Files: `app.py` (all `@app.route` handlers)

**3. No authentication flow tests:**
- Registration validation not tested
- Login/logout not tested
- Session persistence not tested
- Session expiration not tested
- Files: `app.py` lines 646-711, `database.py` lines 127-244

### Significant Gaps (Medium Priority)

**4. No frontend tests:**
- No JavaScript test framework installed
- Complex rendering logic untested (calendar rendering, chart calculations)
- `authFetch()` wrapper behavior untested
- Client-side caching logic untested
- Files: `static/js/dashboard.js`, `static/js/calendar.js`, `static/js/home.js`

**5. No integration tests in CI:**
- Security tests cannot run in CI (require live server + Firestore)
- No test step in `.github/workflows/security-scan.yml`
- No separate CI workflow for tests

**6. No data validation edge case tests:**
- What happens with dates like `2024-02-30`?
- What happens with empty `body_parts` array?
- What happens with very long usernames?
- What happens when Firestore is unreachable mid-request?

### Lower Priority Gaps

**7. No performance/load tests:**
- `database.py` has N+1 query patterns (e.g., `get_weekly_workout_history` makes 12 separate queries)
- No benchmarks for analytics endpoints

**8. No scraping reliability tests:**
- `fetch_entries_data()` HTML parsing not tested with sample HTML
- Session expiration handling not tested

## CI/CD Testing

### Current CI Pipeline: `.github/workflows/security-scan.yml`

**Triggers:**
- Pull requests
- Push to `main`/`master`
- Daily cron at midnight

**Steps (security scanning only, no tests):**
1. Gitleaks secret scanning
2. `safety check --full-report` (dependency vulnerability scan, `continue-on-error: true`)
3. `pip-audit --strict` (dependency audit, `continue-on-error: true`)

**Critical issue:** Both dependency scanners use `continue-on-error: true`, meaning vulnerabilities do NOT fail the build.

**What is missing from CI:**
- No `python -m pytest` or `python -m unittest` step
- No test runner at all
- No coverage reporting
- No frontend linting/testing
- No integration test step
- No Docker build verification

### Pre-commit Hooks: `.pre-commit-config.yaml`

- `trailing-whitespace` fixer
- `end-of-file-fixer`
- `check-yaml`
- `check-added-large-files`
- `gitleaks` (v8.18.1) secret detection

**No test execution in pre-commit hooks.**

## Mocking

**No mocking framework used.**

The existing security tests use live HTTP requests against a running server with real Firestore. No mocking of any kind.

**Recommendation for future tests:**
- Use `unittest.mock` for Firestore client
- Use Flask's built-in test client (`app.test_client()`) instead of `requests`
- Mock `database` module when testing `app.py` routes

## Recommended Test Plan

### Phase 1: Foundation (Highest Impact)

**Add pytest + Flask test client:**
```bash
# Add to requirements.txt (dev section)
pytest>=8.0
pytest-cov>=5.0
```

**Create `tests/conftest.py` with Flask test client fixture:**
```python
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
```

**Unit test `database.py` pure functions first (no Firestore needed):**
- `is_gym_open()` -- 10+ test cases for weekday/weekend/edge hours
- `is_complete_day()` -- test with various hour patterns
- `validate_username()` -- empty, short, long, special chars
- `validate_password()` -- empty, short, long
- `hash_password()` / `verify_password()` -- round-trip test
- Target file: `tests/test_database.py`

### Phase 2: Route Handler Tests

**Test `app.py` with Flask test client (mocking `database` module):**
- Test each route returns correct status codes
- Test input validation rejects bad data
- Test authentication requirement is enforced
- Test admin endpoints reject unauthorized access
- Target file: `tests/test_routes.py`

### Phase 3: Integration Tests

**Refactor `tests/security_tests.py`:**
- Rename to `tests/test_security.py` (pytest convention)
- Add cleanup in `tearDown()`
- Mark with `@pytest.mark.integration` (skip in CI unless Firestore available)
- Target file: `tests/test_security.py`

### Phase 4: CI Integration

**Add test step to `.github/workflows/security-scan.yml` (or new workflow):**
```yaml
- name: Run Tests
  run: |
    pip install pytest pytest-cov
    python -m pytest tests/ -v --cov=. --cov-report=term-missing \
      -k "not integration"  # Skip tests needing Firestore
```

**Remove `continue-on-error: true` from dependency scanners** to enforce security checks.

### Phase 5: Frontend Testing (Stretch)

- Add Jest or Vitest for JavaScript unit tests
- Test `safeSanitize()` behavior when DOMPurify is missing
- Test date formatting and calendar calculation logic
- Test `authFetch()` 401 handling

---

*Testing analysis: 2026-04-04*
