# Project State

**Project:** Gym Tracker  
**Last Updated:** 2026-04-06  
**Phase:** ETAP 2 ZAKONCZONY — Full Audit Implementation Complete

## Current Status

Full audit implementation completed in one session (2026-04-06):
- **11 commits**, 51/55 roadmap tasks done (93%)
- **21/23 security findings fixed** (0 Critical, 0 High remaining)
- **~8,400 LOC removed** (dead files + inline JS)
- **app.py refactored**: 1112 → 427 LOC (4 Flask Blueprints)
- **27 unit tests** + CI smoke tests before deploy
- **Firestore**: composite indexes created, weekly backups enabled
- All audit documents updated to final state

### Architecture After Refactor

```
app.py (427 LOC)          — core: pages, scraper, security headers
extensions.py (24 LOC)    — shared: limiter, auth helpers
routes/
  auth.py (73 LOC)        — register, login, logout, session
  admin.py (189 LOC)      — user mgmt, data reset, debug, export
  workouts.py (181 LOC)   — CRUD, month, dashboard, strength, progression
  analytics.py (204 LOC)  — weekly, heatmap, comparison, best-hours, extended
database.py (1900 LOC)    — Firestore data layer
templates/
  base.html               — shared head, fonts, CSS vars, DOMPurify
  dashboard.html           — extends base, main dashboard
  index.html              — extends base, legacy page
  calendar.html           — extends base, standalone calendar
```

## Key Decisions Remaining

1. Decision on React stats-dashboard (integrate / separate / remove)
2. Decision on Cloud Run authentication (public vs IAP)
3. Credential rotation (ADMIN_SECRET, SECRET_KEY, GYM_PASSWORD) — see PATCH-01/02 in `AUDIT/12_RECOMMENDED_PATCHES.md`

## What's Left (Accepted / Not Critical)

| ID | Item | Reason |
|----|------|--------|
| SEC-14 | setup_server.sh uses curl ifconfig.me | Dev script, low risk |
| SEC-21 | In-memory rate limiter on Cloud Run | Acceptable for hobby project |

## Backlog (Nice to Have)

See `AUDIT/13_ROADMAP.md` "Nice to Have" section — items 41-55 (empty states, mobile heatmap, focus trap, semantic HTML, skeleton loaders, self-hosted fonts, staging env, frontend tests, structured JSON logging, admin audit log).

## Codebase Map

See `.planning/codebase/` for 11 structured documents:
- STACK.md, INTEGRATIONS.md (tech focus)
- ARCHITECTURE.md, STRUCTURE.md (arch focus)
- CONVENTIONS.md, TESTING.md (quality focus)
- CONCERNS.md (risks verified against code)
- RESEARCH_BACKEND.md, RESEARCH_FRONTEND.md, RESEARCH_SECURITY.md, RESEARCH_INFRA.md
