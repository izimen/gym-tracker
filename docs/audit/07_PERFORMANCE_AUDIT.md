# 07 - PERFORMANCE AUDIT

**Agent:** PERFORMANCE / OPTYMALIZACJA  
**Data:** 2026-04-04

---

## Findings

### PERF-01: Firestore N+1 queries w `get_weekly_workout_history()`
- **Severity:** High
- **Lokalizacja:** `database.py:699-746`
- **Opis:** Dla 12 tygodni historia, wykonuje 12 ODDZIELNYCH zapytan do Firestore:
  ```python
  for i in range(weeks - 1, -1, -1):
      docs = db.collection('workouts')\
          .where('date', '>=', start_str)\
          .where('date', '<=', end_str)\
          .stream()
  ```
- **Wplyw:** 12 round-trips do Firestore. Przy latency 50ms/query = 600ms samych zapytan.
- **Rekomendacja:** Jedno zapytanie na caly zakres dat (12 tygodni), potem grupowanie w Pythonie.
- **Effort:** Low | **Impact:** High
- **Estimated improvement:** ~10x redukcja latency tego endpointu

### PERF-02: `get_extended_occupancy_stats()` przetwarza dane wielokrotnie
- **Severity:** High
- **Lokalizacja:** `database.py:1569-1602`
- **Opis:** Pomimo ze `cached_data` jest przekazywany do sub-funkcji, kazda sub-funkcja powtarza te same operacje:
  - `get_daily_averages()` - grupowanie po dacie, filtrowanie complete days
  - `get_hourly_averages()` - grupowanie po dacie, filtrowanie complete days
  - `get_best_day_hour_combos()` - grupowanie po dacie, filtrowanie complete days
  - `get_worst_day_hour_combos()` - grupowanie po dacie, filtrowanie complete days
  
  Kazda funkcja samodzielnie buduje `daily_data` dict, sprawdza `is_complete_day()`, itp.
- **Wplyw:** ~4x duplikacja przetwarzania tych samych danych. Dla 30 dni * 17h = 510 dokumentow, to 2040 iteracji zamiast 510.
- **Rekomendacja:** Preprocessowac dane raz (`group_by_date()` + `filter_complete_days()`) i przekazac przetworzony wynik.
- **Effort:** Medium | **Impact:** High
- **Estimated improvement:** ~3-4x redukcja CPU usage dla tego endpointu

### PERF-03: Brak cache'u na statystyki godzinowe
- **Severity:** Medium
- **Lokalizacja:** `database.py:1135-1161`
- **Opis:** `get_hourly_stats()` i `get_extended_occupancy_stats()` odpytuja Firestore za kazdym razem. Dane zmieniaja sie raz na godzine, ale sa odpytywane przy kazdym request.
- **Wplyw:** Niepotrzebne koszty Firestore i latency.
- **Rekomendacja:** Dodac server-side cache z TTL 5-10 min (np. `functools.lru_cache` z timestamp lub prosty dict cache).
- **Effort:** Low | **Impact:** Medium

### PERF-04: Static assets cache header 1 rok ale bez fingerprinting
- **Severity:** Medium
- **Lokalizacja:** `app.py:992-993`
- **Opis:**
  ```python
  response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
  ```
  Cache 1 rok, ale pliki JS/CSS nie maja fingerprint (hash w nazwie). Po update uzytkownik dostanie stara wersje.
- **Wplyw:** Uzytkownik moze widziec stara wersje JS/CSS po deploymencie.
- **Rekomendacja:** (a) Dodac query string z wersja (`dashboard.js?v=2.0.1`), LUB (b) zmienic cache na `max-age=3600` (1h), LUB (c) uzyc manifest z hashami.
- **Effort:** Low | **Impact:** Medium

### PERF-05: Google Fonts ladowane z CDN bez preload
- **Severity:** Medium
- **Lokalizacja:** `templates/dashboard.html:9-11`, `templates/index.html:8-10`
- **Opis:** Font Inter ladowany z Google Fonts z `preconnect` ale bez `preload`. Font blokuje renderowanie tekstu do zaladowania (FOIT).
- **Wplyw:** Flash of Invisible Text na wolnych polaczeniach.
- **Rekomendacja:** Juz ma `display=swap` co jest dobre. Rozwazyc self-hosting fontow jako static asset.
- **Effort:** Low | **Impact:** Low

### PERF-06: `purify.min.js` ladowany synchronicznie
- **Severity:** Medium
- **Lokalizacja:** `templates/dashboard.html:12`
- **Opis:** `<script src="/static/js/purify.min.js"></script>` - ladowane synchronicznie w `<head>`, blokuje parsing HTML.
- **Wplyw:** Opoznienie First Contentful Paint o czas ladowania DOMPurify.
- **Rekomendacja:** Dodac `defer` lub przeniesc przed `</body>`.
- **Effort:** Low | **Impact:** Low

### PERF-07: Frontend - brak lazy loading zakladek
- **Severity:** Low
- **Lokalizacja:** `static/js/dashboard.js:40-56`
- **Opis:** Zakladki "Statystyki" i "Sila" laduja dane dopiero przy pierwszym kliknieciu - to dobrze. ALE tab-content HTML jest renderowany od razu (wszystkie 4 zakladki w DOM).
- **Wplyw:** Wiekszy initial DOM, ale efekt minimalny.
- **Rekomendacja:** Akceptowalne. Dane sa lazy-loaded co jest najwazniejsze.
- **Effort:** - | **Impact:** Low

### PERF-08: `get_progression()` - brak limitu w query
- **Severity:** Low
- **Lokalizacja:** `database.py:1731`
- **Opis:** `db.collection('workouts').order_by('date').stream()` - laduje WSZYSTKIE workouts, potem `progression[-limit:]`.
- **Wplyw:** Niepotrzebne ladowanie setek dokumentow zeby zwrocic 20.
- **Rekomendacja:** Dodac `.where('user_id', '==', user_id)` i `.limit(limit)` z `.order_by('date', direction=DESCENDING)`.
- **Effort:** Low | **Impact:** Low

### PERF-09: Brak kompresji obrazow
- **Severity:** Low
- **Lokalizacja:** Caly projekt
- **Opis:** Brak obrazow w projekcie (uzywane emoji), wiec nie jest to aktualny problem. Flask-Compress jest wlaczony (gzip).
- **Wplyw:** Brak - pozytywna obserwacja.
- **Rekomendacja:** N/A
- **Effort:** - | **Impact:** -

### PERF-10: `setInterval` na live counter - mozliwe request storm
- **Severity:** Low
- **Lokalizacja:** `static/js/dashboard.js:239` (60s), `templates/index.html:768` (30s)
- **Opis:** Na starej stronie odswiezanie co 30s (entries + stats + workouts), na nowej co 60s. Jesli wielu uzytkownikow jest online jednoczesnie, moze to obciazyc scraper.
- **Wplyw:** Przy 10 uzytkowanych = 10 req/min (dashboard) + 20 req/min (legacy). Akceptowalne.
- **Rekomendacja:** Rozwazyc `requestAnimationFrame` lub `visibility API` zeby nie odswiezac w tle.
- **Effort:** Low | **Impact:** Low
