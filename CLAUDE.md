# CLAUDE.md — Gym Tracker

## Project

CubeFitness Gym Tracker — web app tracking gym occupancy and personal workouts. Deployed on Google Cloud Run, uses Firestore as database.

**URL:** https://gym-tracker-gcy45fsdkq-lm.a.run.app
**Repo:** https://github.com/izimen/gym-tracker

## Stack

- **Backend:** Python 3.12 / Flask / Gunicorn / Firestore
- **Frontend:** Vanilla JS + DOMPurify / Jinja2 templates / CSS (no framework)
- **Infra:** Docker / Cloud Run / GitHub Actions CI/CD
- **Validation:** Pydantic (workout POST), bcrypt (passwords)

## Architecture

```
app.py (415 LOC)         — core: pages, scraper, security headers, CSRF
extensions.py (24 LOC)   — shared: limiter, FIRESTORE_ENABLED, auth helpers
routes/
  auth.py (73 LOC)       — register, login, logout, session
  admin.py (189 LOC)     — user mgmt, data reset, debug, export
  workouts.py (199 LOC)  — CRUD, month, dashboard, strength, progression
  analytics.py (204 LOC) — weekly, heatmap, comparison, best-hours, extended
database.py (1965 LOC)   — Firestore data layer, analytics, account lockout
templates/
  base.html              — shared head, fonts, CSS vars, DOMPurify
  dashboard.html          — main dashboard (extends base)
  index.html             — legacy page (extends base)
  calendar.html          — standalone calendar (extends base)
```

## Key Conventions

- **Blueprints import `extensions` module**, not individual names: `import extensions` then `extensions.FIRESTORE_ENABLED`, `extensions.limiter`, etc.
- **All protected endpoints** use `authFetch()` in JS (adds `credentials: 'same-origin'` + `X-Requested-With: XMLHttpRequest`)
- **Admin endpoints** require `X-Admin-Secret` header, NOT session auth
- **CSRF check** on all POST/PUT/DELETE to `/api/*` — requires `X-Requested-With` header
- **Error responses** use generic messages (`Internal server error`), details logged server-side with `logger.error()`
- **entries_cache** uses atomic dict replacement (full new dict, never `{**old, ...}`)
- **Gym hours:** Mon-Fri 6:00-24:00, Sat-Sun 8:00-20:00 (in `database.py GYM_HOURS`)
- **Polish UI** — all user-facing errors and messages in Polish
- **CSS vars** unified across all pages — canonical values in `base.html`

## Commands

```bash
# Run locally
python app.py

# Run tests
python -m pytest tests/ -v

# Deploy (automatic on push to main via PR)
# CI runs: pip install deps → pytest → deploy to Cloud Run
```

## Branch Protection

- `main` requires PR (no direct push, no force push)
- Security scan + Snyk check on PRs
- Deploy workflow runs pytest smoke tests before Cloud Run deploy

## Environment Variables (GitHub Secrets)

`SECRET_KEY`, `GYM_URL`, `GYM_EMAIL`, `GYM_PASSWORD`, `ADMIN_SECRET`, `GCP_SA_KEY`, `GCP_PROJECT_ID`

## GCP

- **Project:** gym-tracker-480502
- **Region:** europe-central2
- **Firestore indexes:** composite (user_id+date ASC, user_id+date DESC) on `workouts`
- **Backups:** weekly (Sunday), 14-day retention

## Audit Status

Full 360 audit completed and implemented. See `AUDIT/` for 16 documents. Key stats:
- 21/23 security findings fixed (0 Critical, 0 High)
- 27 unit tests + CI smoke tests
- 3 verification agents confirmed: 16/16 endpoints, 19/19 headers, 27/27 tests PASS

## Do NOT

- Add Co-Authored-By lines to commits
- Use `from extensions import X` in blueprints (use `import extensions` + `extensions.X`)
- Use `{**entries_cache, ...}` pattern (race condition — always replace full dict)
- Return `str(e)` in API error responses (log it, return generic message)
- Use plain `fetch()` for protected endpoints in JS (use `authFetch()`)
