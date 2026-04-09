# 02 - ARCHITECTURE AUDIT

**Agent:** REPO MAPPER / ARCHITEKTURA  
**Data:** 2026-04-04

---

## Architektura Ogolna

Aplikacja to **monolityczny serwer Flask** z:
- Wbudowanym scraperem (requests + BeautifulSoup)
- Warstwą Firestore (database.py)
- Server-side rendering (Jinja2 templates)
- Vanilla JS frontend
- Oddzielnym prototypem React (stats-dashboard/)

```
[Browser] <--HTTP--> [Flask/Gunicorn]
                         |
                    [app.py] -----> [database.py] -----> [Firestore]
                         |
                    [Background Thread] -----> [eFitness Portal]
```

---

## Findings

### ARCH-01: Duplikacja kodu w database.py
- **Severity:** Medium
- **Lokalizacja:** `database.py:1261-1377` vs `database.py:1380-1493`
- **Opis:** `get_best_day_hour_combos()` i `get_worst_day_hour_combos()` sa w ~90% identyczne. Roznia sie tylko sortowaniem (ascending vs descending).
- **Wplyw:** 230 linii zduplikowanego kodu. Kazda zmiana logiki wymaga modyfikacji w dwoch miejscach.
- **Rekomendacja:** Wyodrebnic wspólna funkcje `_get_day_hour_combos(sort_ascending=True)`.
- **Effort:** Low | **Impact:** Medium

### ARCH-02: Brak separacji warstw w app.py
- **Severity:** Medium
- **Lokalizacja:** `app.py`
- **Opis:** `app.py` laczy routing, logike biznesowa (scraping), konfiguracje, security headers i admin panel w jednym pliku (1012 LOC). Brak kontrolerow/blueprintow.
- **Wplyw:** Trudne do testowania, rozbudowy i utrzymania. Kazdy endpoint widzi caly kontekst.
- **Rekomendacja:** Rozdzielic na Flask Blueprints: `routes/auth.py`, `routes/api.py`, `routes/admin.py`, `scraper.py`.
- **Effort:** Medium | **Impact:** High

### ARCH-03: Stats-dashboard (React) nie zintegrowany
- **Severity:** Low
- **Lokalizacja:** `stats-dashboard/`
- **Opis:** Oddzielna aplikacja React z komponentami statystyk (charts, heatmap, comparison). Nie ma polaczenia z Flask backendem. Nie jest serwowana ani budowana.
- **Wplyw:** Martwy kod w repo. Jesli planowany jako nastepca vanilla JS, wymaga integracji (proxy Vite lub budowanie do static/).
- **Rekomendacja:** Okreslic cel: (a) zintegrować z Flask jako static build, (b) serwowac oddzielnie, (c) usunac.
- **Effort:** High | **Impact:** Medium

### ARCH-04: In-memory cache bez TTL
- **Severity:** Medium
- **Lokalizacja:** `app.py:115-120`
- **Opis:** `entries_cache` to zwykly dict aktualizowany co 3 minuty przez background thread. Brak TTL, brak invalidacji, brak persistence. Po restarcie kontenera cache jest pusty az do pierwszego fetcha.
- **Wplyw:** Przez pierwsze ~3 min po starcie kontener zwraca `status: initializing`. Na Cloud Run z cold starts to czesty scenariusz.
- **Rekomendacja:** Dodac fallback do ostatniego odczytu z Firestore przy cold start.
- **Effort:** Low | **Impact:** Medium

### ARCH-05: Brak warstwy serwisowej
- **Severity:** Low
- **Lokalizacja:** Caly projekt
- **Opis:** app.py bezposrednio wywoluje database.py. Brak warstwy serwisowej ktora hermetyzowałaby logike biznesowa (np. walidacja, transformacja danych, business rules).
- **Wplyw:** Logika biznesowa rozproszona miedzy app.py i database.py. Testy wymagaja mockowania HTTP i Firestore jednoczesnie.
- **Rekomendacja:** Akceptowalne na obecna skale projektu. Rozwazyc przy dalszym rozwoju.
- **Effort:** High | **Impact:** Low

### ARCH-06: Tight coupling scraper <-> server
- **Severity:** Medium
- **Lokalizacja:** `app.py:127-267`
- **Opis:** Scraper eFitness jest czescia procesu serwera Flask. Background thread dziala w tym samym procesie co obsluga requestow. Blad scrapera nie moze spowodowac restartu scrapera bez restartu serwera.
- **Wplyw:** Bledna sesja scrapera moze wplywac na stabilnosc serwera. Brak mozliwosci niezaleznego skalowania.
- **Rekomendacja:** Na obecna skale akceptowalne (1 instancja). Przy skalowaniu rozwazyc Cloud Scheduler + Cloud Function.
- **Effort:** High | **Impact:** Low

### ARCH-07: Brak schema validation na API
- **Severity:** Medium
- **Lokalizacja:** Wszystkie POST endpointy
- **Opis:** Walidacja danych wejsciowych robiona recznie (if/else). Brak schematu (Marshmallow, Pydantic, jsonschema). Latwość o pominiecie walidacji.
- **Wplyw:** Niespójne walidacje miedzy endpointami. Brak dokumentacji kontraktow API.
- **Rekomendacja:** Dodac schema validation (np. Pydantic lub Marshmallow) dla POST payloads.
- **Effort:** Medium | **Impact:** Medium

### ARCH-08: Circular potential - Flask session name collision
- **Severity:** Low
- **Lokalizacja:** `app.py:137` vs `app.py:49`
- **Opis:** Zmienna `session` z `requests.Session()` (scraper) koliduje z `session` z Flask (`from flask import session`). W app.py `session` w kontekscie requestu to Flask session, ale `session` w `get_gym_session()` to `requests.Session()`. Potencjalna pomylka.
- **Wplyw:** Ryzyko bledow przy modyfikacji kodu.
- **Rekomendacja:** Zmienic nazwe zmiennej scrapera np. na `gym_session` lub `scraper_session`.
- **Effort:** Low | **Impact:** Low
