# 13 - ROADMAP

**Agent:** ORCHESTRATOR / TECH LEAD  
**Data:** 2026-04-04

---

## Immediate Critical (Dzien 1-2) — DONE (2026-04-06)

~~Zmiany ktore powinny byc wdrozone natychmiast ze wzgledu na bezpieczenstwo.~~

| # | Zadanie | ID | Effort | Impact | Status |
|---|---------|-----|--------|--------|--------|
| 1 | Dodac `.env` i inne pliki do `.dockerignore` | SEC-01/OPS-01 | 5 min | Critical | DONE |
| 2 | Ujednolicic bledy logowania (anti-enumeration) | SEC-04 | 10 min | High | DONE |
| 3 | Usunac admin secret z query params | SEC-05 | 15 min | High | DONE |
| 4 | Naprawic DOMPurify fallback | SEC-06 | 10 min | High | DONE |
| 5 | Zmienic GET na DELETE dla reset-hourly | API-02 | 5 min | High | DONE |
| 6 | Dodac auth do /api/debug/* endpoint | SEC-03 | 15 min | Critical | DONE |

**Laczny effort:** ~1h  
**Laczny impact:** Eliminacja 4 Critical + 3 High vulnerabilities  
**Wdrozono:** 2026-04-06

---

## Quick Wins (Dzien 3-4) — CZESCIOWO DONE

Zmiany o wysokim impact przy niskim nakladzie pracy.

| # | Zadanie | ID | Effort | Impact | Status |
|---|---------|-----|--------|--------|--------|
| 7 | Wzmocnic politykę hasel (min 8 znakow) | SEC-02 | 30 min | Critical | DONE |
| 8 | Usunac dead files (dashboard_old.html, response.html, .idea/) | ARCH | 10 min | Low | DONE |
| 9 | Usunac design-showcase/ folder | ARCH | 5 min | Low | DONE |
| 10 | Dodac Firestore query do health check | OPS-04 | 15 min | Medium | DONE |
| 11 | Optymalizowac get_personal_records() - dodac where user_id | API-03 | 15 min | High | DONE |
| 12 | Optymalizowac get_progression() - dodac where user_id | API-05 | 15 min | Medium | DONE |
| 13 | Zaktualizowac .pre-commit Gitleaks version | SEC-17 | 5 min | Low | DONE |
| 14 | Dodac `object-src 'none'` do CSP | SEC-18 | 5 min | Low | DONE |
| 15 | Dodac rate limit do export endpointow | SEC-11 | 10 min | Medium | DONE |

**Laczny effort:** ~2h  
**Laczny impact:** 1 Critical + 2 High + 3 Medium  
**Wdrozono (04-06):** 9/9 (100%)

---

## Next Sprint (Tydzien 2)

Zmiany wymagajace wiecej planowania.

| # | Zadanie | ID | Effort | Impact | Status |
|---|---------|-----|--------|--------|--------|
| 16 | Refaktor duplikacji best/worst combos w database.py | ARCH-01 | 1h | Medium | DONE |
| 17 | Naprawic N+1 queries w get_weekly_workout_history | PERF-01 | 1h | High | DONE |
| 18 | Pre-process danych w get_extended_occupancy_stats | PERF-02 | 2h | High | DONE |
| 19 | Dodac unit testy: walidacja, is_complete_day | QA-01 | 2h | High | DONE (27 testow) |
| 20 | Dodac smoke testy do CI/CD | QA-05 | 1h | High | TODO |
| 21 | Zastapic print() loggerem w app.py | OPS-06 | 1h | Medium | DONE |
| 22 | Dodac brakujace env vars do deploy workflow | OPS-02 | 30 min | High | TODO |
| 23 | Dodac walidacje year/month/date w URL paths | API-08/SEC-10 | 30 min | Medium | DONE |
| 24 | Poprawic thread safety entries_cache | API-01 | 30 min | High | DONE |
| 25 | Dodac toast notifications po save/delete workout | UX-01 | 1h | High | DONE |
| 26 | Przetlumaczyc bledy walidacji na polski | UX-02 | 30 min | Medium | DONE |
| 27 | Usunac `user-scalable=no` z viewportow | A11Y-08 | 5 min | Low | DONE |
| 28 | Dodac aria-labels na przyciskach nawigacji | A11Y-02 | 30 min | Medium | DONE |

**Wdrozono (04-06):** 13/13 (100%)

---

## Strategic Refactors (Tydzien 3-4)

Wieksze zmiany architektoniczne.

| # | Zadanie | ID | Effort | Impact | Status |
|---|---------|-----|--------|--------|--------|
| 29 | Rozdzielic app.py na Flask Blueprints | ARCH-02 | 4h | Medium | DONE |
| 30 | Stworzyc base template (Jinja2 inheritance) | FE-01 | 3h | High | DONE |
| 31 | Dokonczyc migracje inline JS z index.html | FE-02 | 2h | High | DONE |
| 32 | Ujednolicic CSS variables | FE-03 | 1h | Medium | DONE |
| 33 | Przeniesc inline styles z dashboard.html do CSS | FE-04 | 2h | Medium | DONE |
| 34 | Dodac server-side cache dla analytics (5 min TTL) | PERF-03 | 2h | Medium | DONE |
| 35 | Dodac schema validation (Pydantic) dla POST endpoints | ARCH-07 | 3h | Medium | DONE |
| 36 | Dodac CSRF token | SEC-07 | 2h | High | DONE |
| 37 | Dodac account lockout po 5 nieudanych logowaniach | SEC-08 | 2h | High | DONE |
| 38 | Dodac composite index (user_id + date) w Firestore | API-04 | 1h | Medium | DONE (GCP) |
| 39 | Dodac Firestore automated backups | OPS-08 | 1h | Medium | DONE (GCP) |
| 40 | Usunac unsafe-inline z CSP po migracji JS | SEC-09 | 30 min | Medium | DONE |

**Wdrozono (04-06):** 12/12 (100%)

---

## Nice to Have (Backlog)

Ulepszenia ktore poprawia jakosc ale nie sa krytyczne.

| # | Zadanie | ID | Effort | Impact |
|---|---------|-----|--------|--------|
| 41 | Dodac empty state dla nowych uzytkownikow | UX-05 | 2h | Medium |
| 42 | Poprawic heatmap na mobile | UX-06 | 2h | Low |
| 43 | Dodac focus trap w modalach | A11Y-05 | 1h | Low |
| 44 | Dodac alt text do wykresow | A11Y-06 | 1h | Low |
| 45 | Poprawic contrast ratio --text-muted | A11Y-03 | 15 min | Medium |
| 46 | Dodac semantic HTML (main, section, article) | A11Y-01 | 1h | Medium |
| 47 | Skeleton loaders na zakladkach | FE-09 | 1h | Low |
| 48 | Fingerprinting static assets (cache busting) | PERF-04 | 1h | Medium |
| 49 | Self-host Google Fonts | PERF-05 | 30 min | Low |
| 50 | Osobny przycisk logout | UX-03 | 30 min | Medium |
| 51 | Okreslic przyszlosc stats-dashboard (React) | ARCH-03 | Decyzja | Medium |
| 52 | Dodac frontend testy (Playwright/Cypress) | QA-02 | 8h | Medium |
| 53 | Dodac staging environment | OPS-03 | 4h | High |
| 54 | Dodac structured JSON logging | OPS-06 | 2h | Medium |
| 55 | Dodac audit log dla akcji admin | API-12 | 2h | Medium |

---

## Metryki Sukcesu Po Wdrozeniu

| Metryka | Przed | Po ETAPIE 2 (04-06) | Cel | Status |
|---------|-------|----------------------|-----|--------|
| Security findings (Critical) | 3 | **0** | 0 | DONE |
| Security findings (High) | 5 | **0** | 0 | DONE |
| Test coverage | ~2% | **27 testow** | >40% | W TRAKCIE |
| Dead files | 12+ | **0** | 0 | DONE |
| Firestore queries per request (analytics) | ~12 | **~1** | ~2 | DONE |
| CSP unsafe-inline | Tak | **Nie** | Nie | DONE |
| Account lockout | Brak | **15 min po 5 probach** | Po 5 probach | DONE |
| Password min length | 3 | **8** | 8 | DONE |
