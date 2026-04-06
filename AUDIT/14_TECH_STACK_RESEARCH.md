# 14 - TECHNOLOGY RESEARCH SUMMARY

**Data:** 2026-04-04  
**Metoda:** 6 rownolegych agentow gsd-phase-researcher  
**Zrodla:** Training data (cutoff maj 2025) + analiza kodu. Wersje do zweryfikowania online.

---

## Werdykt: Czy uzywamy dobrych technologii?

| Technologia | Werdykt | Uzasadnienie |
|-------------|---------|-------------|
| **Flask 3.x** | ZOSTAW | Idealny dla server-rendered monolitu z Jinja2. Zmiana na FastAPI nie daje korzysci bez rewrite. |
| **Firestore** | ZOSTAW | Prawidlowy wybor. Problemy to zle query patterns, nie ograniczenia Firestore. |
| **Vanilla JS** | ZOSTAW | Przy ~2300 LOC framework jest niepotrzebny. Prog ~4000 LOC. |
| **bcrypt** | ZOSTAW | Cost factor 12 jest poprawny. OWASP-aligned. |
| **Gunicorn** | ZOSTAW | Zmien timeout 0→60. Workers=1, threads=8 poprawne dla 1 vCPU. |
| **Docker Alpine** | ZOSTAW | Akceptowalny. Przy problemach z grpcio → `python:3.12-slim-bookworm`. |
| **Cloud Run** | ZOSTAW | Dodaj min-instances=1, Secret Manager, health probes. |
| **DOMPurify** | ZOSTAW | Nadal standard. Napraw fail-open fallback. |
| **GitHub Actions** | ZOSTAW | Dziala. Dodaj Workload Identity Federation zamiast SA key JSON. |
| **React prototype** | USUN lub ZAMROZ | Nie integruj z Flask. Uzyj jako design reference. |
| **pytz** | **ZAMIEN** | → `zoneinfo` (stdlib od Python 3.9). 29 call sites, mechaniczna zamiana. |
| **requirements.txt >=** | **ZMIEN** | Dodaj lockfile (`pip-compile`). Otwarte zakresy ryzykowne. |

---

## Top 10 Rekomendacji z Researchu

### 1. Zamien `pytz` na `zoneinfo` (stdlib)
- **Zrodlo:** RESEARCH_BACKEND.md (appendix)
- **Effort:** Low (29 identycznych zamian: `pytz.timezone('Europe/Warsaw')` → `ZoneInfo('Europe/Warsaw')`)
- **Impact:** Usunięcie zaleznosci, zgodnosc z nowoczesnym Pythonem
- **Pewnosc:** HIGH

### 2. Dodaj 2 composite indexes w Firestore
- **Zrodlo:** RESEARCH_INFRA.md (appendix)
- **Index 1:** `workouts(user_id ASC, date ASC)`
- **Index 2:** `workouts(user_id ASC, date DESC)`
- **Effort:** Low (konfiguracja w Firestore Console + zmiana queries)
- **Impact:** **80-95% redukcja odczytow Firestore**, ogromne oszczednosci kosztow
- **Pewnosc:** HIGH

### 3. Napraw politykę hasel wg NIST SP 800-63B
- **Zrodlo:** RESEARCH_SECURITY.md, RESEARCH_BACKEND.md
- **Minimum:** 8 znakow (obecne: 3)
- **Maximum:** 72 znaki (obecne: 20, bcrypt limit = 72 bytes)
- **NIE wymagaj:** wielkich liter / cyfr / symboli (NIST zabrania composition rules)
- **DODAJ:** sprawdzanie przeciw liscie popularnych hasel
- **Pewnosc:** HIGH

### 4. Dodaj CSRF ochronę - custom header
- **Zrodlo:** RESEARCH_BACKEND.md
- **Metoda:** Wymagaj `X-Requested-With: XMLHttpRequest` na wszystkich POST endpointach
- **Effort:** Low (~15 linii kodu backend + frontend)
- **Impact:** Ochrona przed cross-site attacks, nawet jesli SameSite zawiedzie
- **Pewnosc:** MEDIUM

### 5. Przenies scraper na Cloud Scheduler
- **Zrodlo:** RESEARCH_INFRA.md
- **Obecnie:** Background thread w procesie Flask (co 3 min)
- **Docelowo:** Cloud Scheduler → HTTP endpoint `/api/internal/scrape` na tym samym serwisie
- **Impact:** Rozwiazuje thread safety (H-06), graceful shutdown (L-03), dziala z scale-to-zero
- **Pewnosc:** HIGH

### 6. Uzyj Google Secret Manager zamiast env vars
- **Zrodlo:** RESEARCH_INFRA.md
- **Obecne:** Env vars ustawiane reczne w Cloud Run Console
- **Docelowe:** Secret Manager + automatyczne montowanie w Cloud Run
- **Impact:** Rozwiazuje C-01, M-05. Centralne zarzadzanie secretami.
- **Pewnosc:** HIGH

### 7. Dodaj Chart.js zamiast recznych wykresow
- **Zrodlo:** RESEARCH_FRONTEND.md
- **Obecne:** 247 LOC recznych wykresow (div bars + SVG)
- **Docelowe:** Chart.js 4.x (~60KB gzipped)
- **Zysk:** Responsywnosc, tooltips, animacje, a11y, -200 LOC
- **Wyjątek:** Heatmap roczna (61 LOC) — zostaw recznie (Chart.js nie ma native heatmap)
- **Pewnosc:** HIGH

### 8. Dodaj esbuild jako minimalny build step
- **Zrodlo:** RESEARCH_FRONTEND.md
- **Obecne:** Brak bundlera, brak minifikacji (tylko gzip od flask-compress)
- **Docelowe:** esbuild bundle + minify JS/CSS
- **Impact:** ~58% redukcja rozmiaru raw, tree-shaking
- **Pewnosc:** HIGH

### 9. Rozważ Firebase Auth (strategiczna decyzja)
- **Zrodlo:** RESEARCH_SECURITY.md
- **Obecne:** Custom auth (bcrypt + Firestore users collection)
- **Docelowe:** Firebase Auth (ten sam GCP project co Firestore)
- **Zysk:** Eliminuje cale kategorie bugow auth (policy, lockout, enumeration, reset, email verification)
- **Migracja:** Mozliwa bez wymuszania zmiany hasel (bcrypt hash import API)
- **Wada:** Dodaje zaleznosc od Firebase SDK, zmiana auth flow
- **Pewnosc:** MEDIUM (wymaga decyzji biznesowej)

### 10. Napraw CI security scan
- **Zrodlo:** RESEARCH_BACKEND.md (appendix)
- **Obecne:** `continue-on-error: true` na Safety + pip-audit → pipeline zawsze przechodzi
- **Docelowe:** Usunac `continue-on-error`, naprawic znalezione podatnosci
- **Impact:** Blokowanie deploy z podatnosciami
- **Pewnosc:** HIGH

---

## Technologie Zweryfikowane jako Poprawne

| Decyzja | Weryfikacja |
|---------|-------------|
| Flask zamiast FastAPI | Flask idealny dla SSR + Jinja2. FastAPI lepszy dla pure API. |
| Firestore zamiast PostgreSQL | Firestore = zero ops, autoscaling, free tier. Dobry dla małej skali. |
| Vanilla JS zamiast React | 2300 LOC nie uzasadnia frameworka. Prog: ~4000 LOC. |
| bcrypt zamiast Argon2 | Oba akceptowalne. bcrypt = szersza kompatybilnosc. |
| Gunicorn zamiast uvicorn | Gunicorn poprawny dla sync Flask. uvicorn dla async. |
| DOMPurify zamiast Sanitizer API | Sanitizer API nie jest jeszcze production-ready. DOMPurify = standard. |
| Cloud Run zamiast App Engine | Cloud Run = wieksza kontrola, Docker, tańszy. |

---

## Dokumenty Researchu (skonsolidowane 6→4)

| Plik | Zawartosc |
|------|-----------|
| `.planning/codebase/RESEARCH_BACKEND.md` | Flask, CSP, CSRF, sessions + Python dependencies |
| `.planning/codebase/RESEARCH_FRONTEND.md` | Vanilla JS, Chart.js, esbuild, DOMPurify |
| `.planning/codebase/RESEARCH_SECURITY.md` | NIST, Firebase Auth, lockout, sessions |
| `.planning/codebase/RESEARCH_INFRA.md` | Cloud Run, Gunicorn, monitoring + Firestore |
