# 04 - BACKEND / API AUDIT

**Agent:** BACKEND / API / LOGIKA BIZNESOWA  
**Data:** 2026-04-04

---

## Endpointy - Przeglad

| Endpoint | Metoda | Auth | Rate Limit | Opis |
|----------|--------|------|------------|------|
| `/` | GET | - | Default | Dashboard HTML |
| `/legacy` | GET | - | Default | Legacy page |
| `/calendar` | GET | - | Default | Calendar HTML |
| `/health` | GET | - | Default | Health check |
| `/api/occupancy` | GET | - | 200/h | Biezace oblozenenie |
| `/api/entries` | GET | - | 200/h | Alias occupancy |
| `/api/stats` | GET | - | 100/h | Statystyki historyczne |
| `/api/refresh` | GET | - | Custom 30s | Wymuszony refresh |
| `/api/workout` | POST | Session | 60/min | Zapis treningu |
| `/api/workout/<date>` | GET | Session | 60/min | Pobranie treningu |
| `/api/workout/<date>` | DELETE | Session | 60/min | Usuwanie treningu |
| `/api/workouts/month/<y>/<m>` | GET | Session | 30/min | Treningi miesieczne |
| `/api/workouts/dashboard` | GET | Session | 30/min | Dashboard stats |
| `/api/analytics/weekly` | GET | Session | 30/min | Tygodniowa historia |
| `/api/analytics/heatmap/<y>` | GET | Session | 30/min | Roczna heatmapa |
| `/api/analytics/comparison` | GET | Session | 30/min | Porownanie miesiecy |
| `/api/analytics/best-hours` | GET | Session | 30/min | Najlepsze godziny |
| `/api/analytics/extended` | GET | Session | 100/h | Rozszerzone statystyki |
| `/api/analytics/new-year` | GET | Session | 100/h | Efekt noworoczny |
| `/api/analytics/completeness/<y>/<m>` | GET | Session | 30/min | Kompletnosc danych |
| `/api/debug/day/<date>` | GET | Admin | 10/min | Debug godzinowy |
| `/api/auth/register` | POST | - | 5/min | Rejestracja |
| `/api/auth/login` | POST | - | 10/min | Logowanie |
| `/api/auth/logout` | POST | - | Default | Wylogowanie |
| `/api/auth/me` | GET | Session | Default | Sprawdzenie sesji |
| `/api/admin/reset-password` | POST | Admin | Default | Reset hasla |
| `/api/admin/users` | GET | Admin | Default | Lista uzytkownikow |
| `/api/admin/reset-hourly` | **DELETE** | Admin | Default | Kasowanie danych |
| `/api/admin/debug-weekday/<wd>` | GET | Admin | Default | Debug weekday |
| `/api/export/workouts` | GET | Admin | 5/h | Eksport treningow |
| `/api/export/full` | GET | Admin | 5/h | Pelny backup |
| `/api/strength` | GET | Session | 30/min | Statystyki sily |
| `/api/progression/<part>` | GET | Session | 30/min | Progresja ciarzaru |

> **Aktualizacja 2026-04-06:** Tabela zaktualizowana po wdrozeniu ETAPU 2 — dodano auth do analytics/debug, rate limits do 15 endpointow, zmieniono metode reset-hourly na DELETE.

---

## Findings

### API-01: Thread safety - `entries_cache` bez synchronizacji
- **Severity:** High
- **Lokalizacja:** `app.py:115-120, 233-247, 282-297`
- **Opis:** `entries_cache` (dict) jest mutowany przez background thread (`background_updater` -> `fetch_entries_data`) i czytany przez request handlery (`get_occupancy`, `get_entries`). Dict w Pythonie NIE jest thread-safe dla operacji read-modify-write.
- **Wplyw:** Potencjalne race conditions prowadzace do blednych danych lub KeyError.
- **Rekomendacja:** Uzyc `threading.Lock()` wokol dostepow do `entries_cache` lub uzyc `queue.Queue`.
- **Effort:** Low | **Impact:** High

### API-02: `/api/admin/reset-hourly` uzywa GET zamiast POST/DELETE
- **Severity:** High
- **Lokalizacja:** `app.py:764-783`
- **Opis:** Endpoint ktory kasuje WSZYSTKIE dane godzinowe uzywa metody GET. GET powinien byc idempotentny i bezpieczny. Destructive operation powinna uzywac DELETE lub POST.
- **Wplyw:** Przypadkowe klikniecie linku, prefetch przegladarki, czy web crawler moze skasowac dane.
- **Rekomendacja:** Zmienic na `methods=['DELETE']` lub `methods=['POST']`.
- **Status:** FIXED (2026-04-06) — zmieniono na DELETE
- **Effort:** Low | **Impact:** High

### API-03: `get_personal_records()` pobiera WSZYSTKIE workouts
- **Severity:** High
- **Lokalizacja:** `database.py:1681-1718`
- **Opis:**
  ```python
  docs = db.collection('workouts').stream()  # WSZYSTKIE workouts ze wszystkich uzytkownikow
  for doc in docs:
      data = doc.to_dict()
      doc_user_id = data.get('user_id', DEFAULT_USER_ID)
      if doc_user_id != user_id:  # filtrowanie w Pythonie
          continue
  ```
- **Wplyw:** Przy 1000 uzytkownikach z 100 treningami kazdy = 100k dokumentow ladowanych do pamieci. Kosztowne ($$$) operacje Firestore.
- **Rekomendacja:** Dodac `.where('user_id', '==', user_id)` do query Firestore.
- **Status:** FIXED (2026-04-06) — `.where('user_id')` dodane + composite index w Firestore
- **Effort:** Low | **Impact:** High

### API-04: `get_month_workouts()` laduje wszystkie workouty z miesiaca
- **Severity:** Medium
- **Lokalizacja:** `database.py:498-525`
- **Opis:** Query filtruje po dacie ale NIE po user_id. Potem filtruje w Pythonie. Przy duzej liczbie uzytkownikow kazdy request laduje workouty WSZYSTKICH uzytkownikow z danego miesiaca.
- **Wplyw:** Nadmierne koszty Firestore i zuzycie pamieci.
- **Rekomendacja:** Dodac composite index (user_id + date) i filtrowac w Firestore.
- **Effort:** Medium | **Impact:** Medium

### API-05: `get_progression()` pobiera WSZYSTKIE workouts posortowane
- **Severity:** Medium
- **Lokalizacja:** `database.py:1721-1756`
- **Opis:** `db.collection('workouts').order_by('date').stream()` - laduje wszystkie workouty, sortuje i filtruje w Pythonie.
- **Wplyw:** To samo co API-03 ale z dodatkowym kosztem sortowania.
- **Rekomendacja:** Dodac `.where('user_id', '==', user_id)` przed `.order_by()`.
- **Status:** FIXED (2026-04-06)
- **Effort:** Low | **Impact:** Medium

### API-06: Brak paginacji na listach danych
- **Severity:** Medium
- **Lokalizacja:** Wiele endpointów: `/api/workouts/month`, `/api/analytics/*`, `/api/export/*`
- **Opis:** Zadne z endpoints nie oferuja paginacji. Przy duzej ilosci danych odpowiedz moze byc bardzo duza.
- **Wplyw:** Timeout, OOM, wolne ladowanie.
- **Rekomendacja:** Dodac `limit` i `offset` parametry, przynajmniej do export endpoints.
- **Effort:** Medium | **Impact:** Medium

### API-07: Niespojne nazewnictwo endpointow
- **Severity:** Medium
- **Lokalizacja:** Cale API
- **Opis:**
  - `/api/occupancy` vs `/api/entries` - dwa endpointy robiace to samo
  - `/api/stats` vs `/api/analytics/extended` - nakladajace sie dane
  - `/api/workouts/dashboard` vs `/api/strength` - niejasna granica
- **Wplyw:** Zdezorientowani klienci API.
- **Rekomendacja:** Deprecate `/api/occupancy` (legacy), ujednolicic naming.
- **Effort:** Low | **Impact:** Low

### API-08: Brak walidacji roku/miesiaca w URL path
- **Severity:** Medium
- **Lokalizacja:** `app.py:438-457, 499-513, 575-589`
- **Opis:** `GET /api/workouts/month/0/0` lub `/api/analytics/heatmap/9999` - brak walidacji zakresu. Moze powodowac nieprzewidywalne zapytania do Firestore.
- **Wplyw:** Bledy runtime, niepotrzebne koszty Firestore.
- **Rekomendacja:** Dodac walidacje: year 2020-2100, month 1-12.
- **Effort:** Low | **Impact:** Low

### API-09: `get_history_count()` liczy dokumenty przy kazdym requeście
- **Severity:** Low
- **Lokalizacja:** `database.py:362-370`
- **Opis:** Komentarz mowi "cached to avoid expensive query" ale w rzeczywistosci nie ma cache. Kazde wywolanie `get_stats()` liczy wszystkie dokumenty.
- **Wplyw:** Koszty Firestore rosna z iloscia danych.
- **Rekomendacja:** Dodac cache z TTL (np. 5 min).
- **Effort:** Low | **Impact:** Low

### API-10: `/api/export/full` - brak filtrowania po user_id
- **Severity:** Low
- **Lokalizacja:** `database.py:1660-1674`
- **Opis:** `export_full_backup()` exportuje workouty WSZYSTKICH uzytkownikow. Admin moze widziec dane wszystkich uzytkownikow.
- **Wplyw:** Oczekiwane dla admin, ale warto to udokumentowac.
- **Rekomendacja:** Dodac informacje w dokumentacji ze export zawiera dane wszystkich uzytkownikow.
- **Effort:** Low | **Impact:** Info

### API-11: `save_workout` nie sanityzuje `notes` field
- **Severity:** Low
- **Lokalizacja:** `app.py:367-401`
- **Opis:** `notes = data.get('notes')` zapisywane bezposrednio do Firestore bez sanityzacji. Frontend nie wyswietla notatek w obecnej wersji, ale jesli zostana dodane, potencjalne XSS.
- **Wplyw:** Stored XSS w przyszlosci jesli notes beda renderowane.
- **Rekomendacja:** Sanityzowac `notes` po stronie serwera lub upewnic sie ze frontend uzywa `textContent`.
- **Effort:** Low | **Impact:** Low

### API-12: Brak logowania akcji admina
- **Severity:** Low
- **Lokalizacja:** Endpointy admin
- **Opis:** Akcje admina (reset hasla, lista uzytkownikow, reset danych) nie sa logowane do zadnego audit logu.
- **Wplyw:** Brak sciezki audytu dla akcji administracyjnych.
- **Rekomendacja:** Dodac structured logging dla akcji admin.
- **Effort:** Low | **Impact:** Medium
