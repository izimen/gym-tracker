# 11 - APPLIED FIXES CHANGELOG

**Agent:** ORCHESTRATOR  
**Data:** 2026-04-04

---

## Status: ETAP 2 - WDROZENIE (2026-04-06)

Ponizej lista wdrozonych zmian z ETAPU 2.

---

## Wdrozone Zmiany

| # | Data | ID | Opis zmiany | Plik(i) | Ryzyko | Status |
|---|------|----|-------------|---------|--------|--------|
| 1 | 2026-04-06 | SEC-01/OPS-01 | Dodano `.env`, `.env.*`, `*.env`, `.idea/`, `design-showcase/`, `AUDIT/`, `.planning/`, `.claude/`, `tests/`, `scripts/`, `stats-dashboard/` do `.dockerignore` | `.dockerignore` | Zerowe | DONE |
| 2 | 2026-04-06 | SEC-04/SEC-22 | Ujednolicono bledy logowania na "Invalid username or password" + dummy bcrypt check dla timing attack prevention | `database.py` | Zerowe | DONE |
| 3 | 2026-04-06 | SEC-05 | Usunieto `request.args.get('secret')` z 6 endpointow admin — tylko header `X-Admin-Secret` | `app.py` | Niskie | DONE |
| 4 | 2026-04-06 | SEC-02 | Wzmocniono politykę hasel: min 8, max 128, wymagana cyfra/wielka litera/znak specjalny | `database.py` | Niskie | DONE |
| 5 | 2026-04-06 | SEC-03 | Dodano auth: `/api/debug/*` wymaga admin secret, analytics endpoints wymagaja session auth | `app.py` | Niskie | DONE |
| 6 | 2026-04-06 | SEC-06 | Naprawiono DOMPurify fallback — zamiast surowego HTML, fallback uzywa `textContent` do strip tags (5 lokalizacji) | `dashboard.js`, `calendar.js`, `home.js`, `index.html`, `calendar.html` | Zerowe | DONE |
| 7 | 2026-04-06 | API-02 | Zmieniono `GET /api/admin/reset-hourly` na `DELETE` | `app.py` | Niskie | DONE |
| 8 | 2026-04-06 | ARCH | Usunieto dead files: `dashboard_old.html`, `response.html`, `design-showcase/` (9 plikow), `.idea/` (10 plikow) — ~6,800 LOC | root, `design-showcase/`, `.idea/` | Zerowe | DONE |
| 9 | 2026-04-06 | SEC-10/SEC-12/SEC-13/SEC-15/SEC-18 | Security hardening: walidacja daty w debug, `object-src 'none'` w CSP, `X-XSS-Protection: 0`, walidacja body_parts w progression, maskowanie bledow wewnetrznych | `app.py` | Zerowe | DONE |
| 10 | 2026-04-06 | SEC-11/SEC-23 | Dodano rate limits do 15 endpointow: 30/min analytics, 60/min CRUD, 10/min debug, 5/hr export | `app.py` | Zerowe | DONE |

---

## Zmiany Planowane (Nie Wdrozone - Wymagaja Wiecej Pracy)

| # | ID | Opis | Powod odlozenia |
|---|-----|------|-----------------|
| 9* | API-03/API-05/PERF-01 | Optymalizacja Firestore queries (dodac `.where('user_id')`) | Wymaga composite index w Firestore + testy |
| 10* | ARCH-01 | Refaktor duplikacji best/worst combos w database.py | Wymaga testow jednostkowych |

---

## Podsumowanie Wdrozenia

- **Zmian wdrozonych:** 10
- **Findings naprawionych:** 17 (SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, SEC-10, SEC-11, SEC-12, SEC-13, SEC-15, SEC-18, SEC-22, SEC-23, API-02, FE-07 czesciowo, dead files)
- **LOC usuniete:** ~6,800 (dead files)
- **LOC zmodyfikowane:** ~150 (app.py + database.py + JS files)
- **Pliki dotknięte:** 8 zmodyfikowanych + 21 usunietych = 29 plikow
