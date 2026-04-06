# Project State

**Project:** Gym Tracker  
**Last Updated:** 2026-04-06  
**Phase:** ETAP 2 Wdrozony — Security & Cleanup Fixes Applied

## Current Status

ETAP 2 implementation completed (2026-04-06):
- **15 findings fixed** across security, backend API, and frontend
- **~6,800 LOC removed** (dead files: dashboard_old.html, response.html, design-showcase/, .idea/)
- **0 Critical findings remaining** (was 4)
- **3 High findings remaining** (was 5+): CSRF, account lockout, thread safety
- All audit documents updated to reflect current state

Previous: Full 360-degree audit completed in read-only mode (2026-04-04):
- 16 audit documents in `AUDIT/`
- 11 codebase analysis documents in `.planning/codebase/`
- 91 unique findings identified, 15 now fixed

## Key Decisions Pending

1. ~~Approval to proceed to ETAP 2~~ DONE
2. Decision on React stats-dashboard (integrate / separate / remove)
3. Decision on Cloud Run authentication (public vs IAP)
4. Credential rotation (ADMIN_SECRET, SECRET_KEY, GYM_PASSWORD)

## Next Priority Items

1. Add unit tests (auth flow, workout CRUD, password validation)
2. Optimize Firestore queries (add `.where('user_id')`)
3. Add CSRF tokens (Flask-WTF or custom header)
4. Add account lockout after failed logins
5. Fix thread safety on entries_cache

## Codebase Map

See `.planning/codebase/` for 7 structured documents:
- STACK.md, INTEGRATIONS.md (tech focus)
- ARCHITECTURE.md, STRUCTURE.md (arch focus)
- CONVENTIONS.md, TESTING.md (quality focus)
- CONCERNS.md (risks verified against code)
