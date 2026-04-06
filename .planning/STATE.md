# Project State

**Project:** Gym Tracker  
**Last Updated:** 2026-04-06  
**Phase:** FULLY COMPLETE — Audited, Fixed, Verified, Deployed, Live

## Current Status

Full audit implementation + bugfix hardening completed (2026-04-06):
- **51/55 roadmap tasks** done (93%) + **8 additional bugfix PRs** (#29-36)
- **21/23 security findings fixed** (0 Critical, 0 High remaining)
- **~8,400 LOC removed** (dead files + inline JS)
- **app.py refactored**: 1112 → 427 LOC (4 Flask Blueprints)
- **27 unit tests** + CI smoke tests before deploy
- **Firestore**: composite indexes created, weekly backups enabled
- **GitHub Secrets**: GYM_URL, GYM_EMAIL, GYM_PASSWORD, ADMIN_SECRET configured
- **stats-dashboard/** React prototype removed, added to .gitignore
- **Co-Authored-By** removed from all commit history
- All audit documents updated to final state

### Verification (3 agents confirmed)

- **16/16 endpoints PASS**
- **19/19 security headers PASS**
- **27/27 tests PASS**

### PRs #29-36 Summary

| PR | Fix |
|----|-----|
| #29 | 5 dashboard.js fetch() calls missing auth (authFetch) |
| #30 | sorted_hours not defined in _get_day_hour_combos (analytics 500) |
| #31 | Cache bust dashboard.js?v=2.2, password maxlength 128 |
| #32 | CSP — restored unsafe-inline for onclick handlers |
| #33 | Export buttons show toast instead of logging out user |
| #34 | 6 bugs: entries_cache race, duplicate logging, CSP unused CDNs, GYM_URL guard, dead code |
| #35 | First-hour stat inflation fix, lockout epoch timestamps, import-by-reference |
| #36 | Added stats-dashboard/ and node_modules/ to .gitignore |

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

1. ~~Decision on React stats-dashboard~~ — DONE (removed, added to .gitignore)
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
