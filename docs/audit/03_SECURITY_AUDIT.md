# 03 - SECURITY AUDIT

**Agent:** SECURITY / APPSEC / SECRETS  
**Data:** 2026-04-04  
**Metodologia:** OWASP ASVS 4.0 + Secure Code Review

---

## Podsumowanie

| Severity | Ilosc | Naprawione (2026-04-06) |
|----------|-------|-------------------------|
| Critical | 3 | 3 FIXED |
| High | 5 | **5 FIXED** |
| Medium | 6 | **5 FIXED** (1 open: SEC-14 setup_server.sh) |
| Low | 4 | **4 FIXED** |
| Info | 2 | - |

> **21 z 23 findings naprawionych.** Otwarte: SEC-14 (setup_server.sh curl, niskie ryzyko), SEC-21 (in-memory rate limiter, akceptowalne dla hobby projektu).

---

## CRITICAL

### SEC-01: `.dockerignore` nie wyklucza `.env` - wyciek credentials do obrazu Docker
- **Severity:** Critical
- **Lokalizacja:** `.dockerignore`, `Dockerfile:9` (`COPY . ./`)
- **Dowod:** `.dockerignore` zawiera: `Dockerfile, README.md, *.pyc, *.pyo, *.pyd, __pycache__, .pytest_cache, venv, .venv, .git, .gitignore, uruchom.bat, setup_server.sh` - BRAK `.env`
- **Scenariusz ataku:** Developer lub CI pipeline buduje obraz Docker z `.env` na dysku. Obraz trafia do rejestru (GCR, Docker Hub). Kazdy z dostepem do rejestru ma dostep do hasel.
- **Wplyw:** Wyciek: GYM_EMAIL, GYM_PASSWORD, ADMIN_PASSWORD, ADMIN_SECRET, SECRET_KEY
- **Rekomendacja:** Dodac `.env`, `.env.*`, `*.env` do `.dockerignore`. Natychmiast.
- **Status:** FIXED (2026-04-06)
- **Wymaga ETAPU 2:** ~~Tak~~ Wdrozone

### SEC-02: Polityka hasel - minimum 3 znaki, brak wymagan zlozonosci
- **Severity:** Critical
- **Lokalizacja:** `database.py:143-154`
- **Dowod:**
  ```python
  def validate_password(password: str) -> tuple:
      if len(password) < 3:
          return False, "Password must be at least 3 characters"
      if len(password) > 20:
          return False, "Password must be at most 20 characters"
      return True, None
  ```
- **Scenariusz ataku:** Haslo "abc" jest akceptowane. Przy rate limit 10/min = 600/h, slownik 1000 najpopularniejszych hasel zlaman w ~2h.
- **Wplyw:** Kompromitacja kont uzytkownikow. Dostep do danych treningowych.
- **Rekomendacja:** Minimum 8 znakow. Dodac sprawdzenie: wielka litera, cyfra LUB znak specjalny. Podniesc max do 128.
- **Status:** FIXED (2026-04-06) — min 8, max 128, wymaga digit/upper/special
- **Wymaga ETAPU 2:** ~~Tak~~ Wdrozone

### SEC-03: Endpointy debug/analytics bez uwierzytelniania
- **Severity:** Critical
- **Lokalizacja:**
  - `app.py:592` - `GET /api/debug/day/<date>` - BRAK AUTH
  - `app.py:533` - `GET /api/analytics/best-hours` - BRAK AUTH
  - `app.py:546` - `GET /api/analytics/extended` - BRAK AUTH
  - `app.py:560` - `GET /api/analytics/new-year` - BRAK AUTH
  - `app.py:575` - `GET /api/analytics/completeness/<y>/<m>` - BRAK AUTH
- **Dowod:** Porównanie z endpointami chronionym: `/api/workout` uzywa `require_login()`, ale wyzej wymienione tego nie robia.
- **Scenariusz ataku:** `curl https://app-url/api/debug/day/2026-04-01` - zwraca surowe dane godzinowe o oblozeneniu.
- **Wplyw:** Wyciek danych biznesowych o frekwencji silowni. Endpoint debug powinien byc wylacznie admin.
- **Rekomendacja:** (a) `/api/debug/*` - dodac admin secret, (b) analytics endpoints - ocenic czy powinny wymagac auth.
- **Status:** FIXED (2026-04-06) — debug wymaga admin secret, analytics wymaga session auth
- **Wymaga ETAPU 2:** ~~Tak~~ Wdrozone

---

## HIGH

### SEC-04: Enumeracja uzytkownikow - rozne komunikaty bledow
- **Severity:** High
- **Lokalizacja:** `database.py:234`
- **Dowod:**
  ```python
  if not user_doc:
      return {'success': False, 'error': 'User not found'}  # <-- ujawnia ze user NIE istnieje
  if not verify_password(...):
      return {'success': False, 'error': 'Wrong password'}   # <-- ujawnia ze user ISTNIEJE
  ```
- **Scenariusz ataku:** Atakujacy wysyla loginy: "admin" -> "Wrong password" (istnieje!), "kuba" -> "User not found" (nie istnieje).
- **Wplyw:** Ułatwia celowany brute-force na istniejace konta.
- **Rekomendacja:** Zmienić oba komunikaty na generyczny "Invalid username or password".
- **Status:** FIXED (2026-04-06) — oba komunikaty zmienione + dummy bcrypt check (SEC-22)

### SEC-05: Admin secret w query string
- **Severity:** High
- **Lokalizacja:** `app.py:722,749,771,792,868,893`
- **Dowod:**
  ```python
  secret = request.headers.get('X-Admin-Secret') or request.args.get('secret') or ''
  ```
- **Scenariusz ataku:** `GET /api/admin/users?secret=H3XTJ8gF...` - secret widoczny w: logach serwera, historii przegladarki, logach proxy/CDN, referrer headers.
- **Wplyw:** Wyciek admin secret. Pelny dostep do admin API.
- **Rekomendacja:** Usunac `request.args.get('secret')`. Wymagac wylacznie headera `X-Admin-Secret`.
- **Status:** FIXED (2026-04-06) — usunieto z 6 endpointow

### SEC-06: DOMPurify fallback zwraca surowy HTML
- **Severity:** High
- **Lokalizacja:** `static/js/dashboard.js:6-12`, `templates/index.html:613-619`
- **Dowod:**
  ```javascript
  function safeSanitize(html) {
      if (typeof DOMPurify !== 'undefined') {
          return DOMPurify.sanitize(html);
      }
      console.warn('DOMPurify not loaded, falling back to raw HTML');
      return html;  // <-- XSS if DOMPurify fails to load
  }
  ```
- **Scenariusz ataku:** Jesli CDN dla purify.min.js jest niedostepny lub plik uszkodzony, cala ochrona XSS jest wylaczona. Dane z API (np. nazwa body part, notes) renderowane surowo.
- **Wplyw:** Stored XSS jesli atakujacy uzyje zlośliwego payloadu w danych.
- **Rekomendacja:** (a) Fallback powinien zwracac pusty string lub text-only, NIE surowy HTML. (b) Uzyc `textContent` zamiast `innerHTML` gdzie mozliwe.
- **Status:** FIXED (2026-04-06) — fallback uzywa textContent do escape HTML (5 lokalizacji)

### SEC-07: Brak CSRF tokens na formularzach
- **Severity:** High
- **Lokalizacja:** Wszystkie POST endpointy
- **Dowod:** Zadna z tras POST nie sprawdza CSRF tokena. Ochrona opiera sie wylacznie na `SESSION_COOKIE_SAMESITE='Lax'`.
- **Scenariusz ataku:** SameSite Lax chroni przed cross-site POST, ale nie przed subdomain attacks ani same-site scenarios. Bez tokenu CSRF, formularz z tej samej domeny moze wykonac nieautoryzowana akcje.
- **Wplyw:** Mozliwosc wykonania akcji w imieniu zalogowanego uzytkownika (zapis/usuwanie treningu).
- **Rekomendacja:** Dodac Flask-WTF lub reczna generacje CSRF tokenu.
- **Status:** FIXED (2026-04-06) — X-Requested-With header validation na POST/PUT/DELETE

### SEC-08: Brak account lockout
- **Severity:** High
- **Lokalizacja:** `app.py:672-695`, `database.py:214-244`
- **Dowod:** Rate limit 10 loginow/min, ale brak blokady konta po N nieudanych probach. Atakujacy moze probowac 10 hasel/min = 600/h = 14400/dzien.
- **Scenariusz ataku:** Z polityka hasel min 3 znaki (SEC-02), slownikowy atak jest realny.
- **Wplyw:** Kompromitacja kont uzytkownikow.
- **Rekomendacja:** Dodac tymczasowa blokade (np. 15 min po 5 nieudanych) lub exponential backoff.
- **Status:** FIXED (2026-04-06) — 15 min lockout po 5 nieudanych probach, Firestore login_attempts

---

## MEDIUM

### SEC-09: CSP pozwala na `unsafe-inline` dla skryptów
- **Severity:** Medium
- **Lokalizacja:** `app.py:978-989`
- **Dowod:**
  ```python
  "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
  ```
- **Wplyw:** `unsafe-inline` oslabnia ochrone CSP przed XSS. Atakujacy ktory wstrzyknie inline script (np. przez DOM injection) omija CSP.
- **Rekomendacja:** Usunac `unsafe-inline` po zakonczonej migracji inline JS (zob. zmiany.md). Uzyc nonce-based CSP.
- **Status:** FIXED (2026-04-06) — inline JS wyekstrahowany, unsafe-inline usunieto z script-src

### SEC-10: Brak walidacji `date_str` w debug endpoint
- **Severity:** Medium
- **Lokalizacja:** `app.py:592-639`
- **Dowod:** `GET /api/debug/day/<date_str>` - brak walidacji formatu. Parsowanie `parts = date_str.split('-')` z `int()` moze rzucic wyjatki ujawniajace stack trace.
- **Wplyw:** Information disclosure przy nieprawidlowym formacie daty.
- **Rekomendacja:** Dodac walidacje regex jak w `/api/workout` (linia 381).
- **Status:** FIXED (2026-04-06) — dodano walidacje `^\d{4}-\d{2}-\d{2}$`

### SEC-11: Export endpoints bez rate limiting
- **Severity:** Medium
- **Lokalizacja:** `app.py:861-904`
- **Dowod:** `/api/export/workouts` i `/api/export/full` nie maja dekoratora `@limiter.limit()`.
- **Wplyw:** Atakujacy z admin secret moze wielokrotnie pobierac pelne backup data, obciazajac Firestore.
- **Rekomendacja:** Dodac rate limit np. "5 per hour".
- **Status:** FIXED (2026-04-06) — dodano `@limiter.limit("5 per hour")`

### SEC-12: Error responses ujawniaja wewnetrzne informacje
- **Severity:** Medium
- **Lokalizacja:** Wiele endpointów, np. `app.py:400-401`, `app.py:417-418`
- **Dowod:**
  ```python
  except Exception as e:
      return jsonify({'error': str(e)}), 500  # <-- raw exception message
  ```
- **Wplyw:** Stack trace, nazwy klas Firestore, sciezki plikow moga byc ujawnione.
- **Rekomendacja:** W produkcji zwracac generyczny "Internal server error". Logowac szczegoły po stronie serwera.
- **Status:** FIXED (2026-04-06) — wszystkie `str(e)` zamienione na generyczny komunikat + `app.logger.error()`

### SEC-13: Brak walidacji `body_parts` w progression endpoint
- **Severity:** Medium
- **Lokalizacja:** `app.py:924-942`
- **Dowod:** `GET /api/progression/<part>` - `part` przekazywany bezposrednio do `database.get_progression()` bez walidacji czy nalezy do `BODY_PARTS.keys()`.
- **Wplyw:** Mozliwosc query Firestore z dowolnym kluczem. Nie prowadzi do injection (Firestore API jest safe), ale zwraca puste dane bez informacji o bledzie.
- **Rekomendacja:** Sprawdzic czy `part in database.BODY_PARTS`, zwrocic 400 jesli nie.
- **Status:** FIXED (2026-04-06) — dodano walidacje przed query

### SEC-14: `setup_server.sh` uzywa curl do pobrania IP
- **Severity:** Medium
- **Lokalizacja:** `setup_server.sh:65`
- **Dowod:** `curl -s ifconfig.me` - zewnetrzny serwis do pobrania publicznego IP. Moze byc przechwycony.
- **Wplyw:** W izolacji niskie ryzyko, ale w kontekscie skryptu instalacyjnego moze ujawnic IP serwera.
- **Rekomendacja:** Zamienic na `hostname -I | awk '{print $1}'` dla IP wewnetrznego.
- **Status:** proposed

---

## LOW

### SEC-15: Header `X-XSS-Protection` jest deprecated
- **Severity:** Low
- **Lokalizacja:** `app.py:970`
- **Dowod:** `response.headers['X-XSS-Protection'] = '1; mode=block'` - nowoczesne przegladarki ignoruja ten header na rzecz CSP.
- **Rekomendacja:** Usunac lub ustawic na `0` (wylaczone). CSP zapewnia ochrone.
- **Status:** FIXED (2026-04-06) — ustawiono na `0`

### SEC-16: Session lifetime 365 dni
- **Severity:** Low
- **Lokalizacja:** `app.py:53`
- **Dowod:** `app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)`
- **Wplyw:** Sesja wazna rok. Jesli cookie wycieknie, atakujacy ma dlugookresowy dostep.
- **Rekomendacja:** Zmniejszyc do 30-90 dni. Dodac mechanizm "remember me" z oddzielnym tokenem.
- **Status:** FIXED (2026-04-06) — zmniejszono do 90 dni

### SEC-17: Pre-commit Gitleaks rev outdated
- **Severity:** Low
- **Lokalizacja:** `.pre-commit-config.yaml:12`
- **Dowod:** `rev: v8.18.1` - aktualna wersja Gitleaks to v8.21+. Brakuje najnowszych regul detekcji.
- **Rekomendacja:** Zaktualizowac do najnowszej wersji.
- **Status:** FIXED (2026-04-06) — zaktualizowano do v8.22.1

### SEC-18: Brak `object-src 'none'` w CSP
- **Severity:** Low
- **Lokalizacja:** `app.py:978-989`
- **Dowod:** CSP nie zawiera `object-src 'none'`. Domyslnie `object-src` dziedziczy z `default-src 'self'`, co pozwala na osadzenie obiektow z tej samej domeny.
- **Rekomendacja:** Dodac `object-src 'none'` do CSP.
- **Status:** FIXED (2026-04-06)

### SEC-21: Rate limiter uzywa in-memory storage (Cloud Run auto-scaling)
- **Severity:** Low
- **Lokalizacja:** `app.py:64-68`
- **Dowod:** `storage_uri="memory://"` - kazda instancja Cloud Run ma wlasne liczniki. Atakujacy trafiajacy na rozne instancje mnozy limit.
- **Wplyw:** Na hobby projekcie akceptowalne. Na produkcji z auto-scalingiem rate limiting jest nieskuteczny.
- **Rekomendacja:** Dla produkcji: Redis-backed storage lub Cloud Run built-in rate limiting.
- **Status:** proposed

### SEC-22: Brak timing attack prevention przy nieistniejacym userze
- **Severity:** Low
- **Lokalizacja:** `database.py:233`
- **Dowod:** Jesli user nie istnieje, bcrypt.checkpw() nie jest wywolywany - odpowiedz wraca szybciej niz przy blednym hasle.
- **Wplyw:** Timing side-channel pozwala okreslic czy user istnieje (szybsza odpowiedz = user nie istnieje).
- **Rekomendacja:** Dodac dummy bcrypt hash check gdy user nie znaleziony.
- **Status:** FIXED (2026-04-06) — dummy bcrypt check dodany razem z SEC-04

### SEC-23: 13 endpointow bez dedykowanego rate limit
- **Severity:** Medium
- **Lokalizacja:** `app.py` - endpointy workout CRUD, analytics, strength, progression, debug
- **Dowod:** Endpointy `/api/workout`, `/api/analytics/weekly`, `/api/analytics/heatmap`, `/api/analytics/comparison`, `/api/analytics/best-hours`, `/api/analytics/completeness`, `/api/debug/day`, `/api/strength`, `/api/progression` - brak `@limiter.limit()` dekoratora (uzyja global default 1000/day, 150/h).
- **Wplyw:** Endpointy z ciezkimi zapytaniami Firestore (full collection scans) moga byc naduzywane.
- **Rekomendacja:** Dodac `@limiter.limit("30 per minute")` dla analytics, `@limiter.limit("60 per minute")` dla CRUD.
- **Status:** FIXED (2026-04-06) — 15 endpointow z rate limits

---

## INFO

### SEC-19: `.env` nie jest w git history
- **Severity:** Info
- **Lokalizacja:** `.gitignore`, git history
- **Dowod:** `git log --all -p -- ".env"` zwraca puste wyniki. `.gitignore` zawiera `.env`.
- **Wplyw:** Pozytywne - credentials nie wyciekly do historii git.

### SEC-20: Dobre praktyki juz wdrozone
- **Severity:** Info
- **Opis:**
  - bcrypt do hashowania hasel
  - Server-side sessions (nie localStorage dla auth)
  - `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`
  - HSTS z `includeSubDomains`
  - `Permissions-Policy` blokuje kamera/mikrofon/lokalizacja
  - `timing-safe comparison` dla admin secret (`secrets.compare_digest`)
  - IDOR fix (user_id z sesji, nie z payloadu)
  - DOMPurify na frontendzie
  - Rate limiting na auth endpointach
  - Gitleaks w pre-commit i CI
