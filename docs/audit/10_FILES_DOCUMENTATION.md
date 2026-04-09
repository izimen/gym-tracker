# 10 - FILES DOCUMENTATION

**Agent:** DOKUMENTACJA / KNOWLEDGE BASE  
**Data:** 2026-04-04

---

## Pliki i Foldery - Pelna Tabela

### / (root)

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| `app.py` | Glowny serwer Flask. Routing, scraping, API endpointy, security headers. 1012 LOC. | `database.py`, `templates/*`, `static/*` | Thread safety entries_cache, otwarte debug endpointy | Rozdzielic na blueprints, naprawic thread safety |
| `database.py` | Warstwa dostepu do Firestore. Auth, workouts, analytics, exports. 2060 LOC. | `google.cloud.firestore`, `bcrypt` | N+1 queries, slaba walidacja hasel, duplikacja kodu | Optymalizowac queries, wzmocnic walidacje |
| `.env` | Realne credentials (NIE w git). | `app.py` (os.environ) | Na dysku z hasami. `.dockerignore` nie wyklucza. | Dodac do `.dockerignore` |
| `.env.example` | Szablon zmiennych srodowiskowych. | Dokumentacja | Brak. Dobrze udokumentowany. | OK |
| `requirements.txt` | Zaleznosci Python. 17 pakietow. | pip, Dockerfile | Brak pinowania dokladnych wersji (uzywa `>=`) | Rozwazyc `requirements.lock` lub pin versions |
| `Dockerfile` | Obraz Docker: python:3.12-alpine. | `requirements.txt`, `.dockerignore` | COPY . ./ kopiuje .env jesli istnieje | Naprawic `.dockerignore` |
| `.dockerignore` | Docker ignore rules. | Dockerfile | ~~BRAK .env~~ FIXED | FIXED (2026-04-06) — .env i 10+ wpisow dodanych |
| `.gitignore` | Git ignore rules. | git | Ma .env - poprawne | OK |
| `.pre-commit-config.yaml` | Pre-commit hooks: trailing whitespace, Gitleaks. | git hooks | Gitleaks rev outdated (v8.18.1) | Zaktualizowac |
| `README.md` | Dokumentacja projektu. Dobrze napisana. | - | Brak API docs dla nowych endpointow (strength, progression) | Uzupelnic |
| `SECURITY.md` | Polityka bezpieczenstwa. | - | Brak email kontaktowego | Dodac email |
| `LICENSE` | MIT License | - | Brak | OK |
| `zmiany.md` | Changelog zmian (2026-01-10). | - | Nieaktualizowany od 3 miesiecy | Zaktualizowac lub usunac |
| `dashboard_old.html` | ~~**DEAD FILE** - stary dashboard~~ | - | ~~Martwy kod~~ | USUNIETO (2026-04-06) |
| `response.html` | ~~**DEAD FILE** - stara wersja strony~~ | - | ~~Martwy kod~~ | USUNIETO (2026-04-06) |
| `uruchom.bat` | Windows batch: uruchamia Flask | `app.py` | Niszowy, prawdopodobnie nieuzywany | Rozwazyc usuniecie |
| `setup_server.sh` | Instalacja na Linux VPS | `requirements.txt` | Brak HTTPS, uzywa curl ifconfig.me | Poprawic |

### templates/

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| `dashboard.html` | **GLOWNY** dashboard. Kalendarz, statystyki, sila, eksport. 541 LOC. | `dashboard.js`, `dashboard.css`, `purify.min.js` | Inline CSS, brak semantic HTML | Wyniesc inline styles |
| `calendar.html` | Standalone kalendarz treningowy. 1433 LOC. | `calendar.js`, `calendar.css` | Duplikacja z dashboard, inline CSS | Rozwazyc redirect do dashboard |
| `index.html` | Legacy strona glowna. 852 LOC. | `home.js`, `home.css`, `purify.min.js` | Inline JS blokuje strict CSP | Dokonczyc migracje JS |

### static/js/

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| `dashboard.js` | Logika glowna: auth, kalendarz, wykresy, modal, export. 1457 LOC. | `dashboard.html`, API endpointy | Niespojne uzycie safeSanitize, magiczne stale | Ujednolicic sanityzacje |
| `calendar.js` | Logika standalone kalendarza. 583 LOC. | `calendar.html`, API endpointy | Duplikacja logiki z dashboard.js | Rozwazyc usuniecie |
| `home.js` | Logika legacy strony. 253 LOC. | `index.html`, API endpointy | Czesciowy - index.html ma tez inline JS | Dokonczyc migracje |
| `purify.min.js` | DOMPurify (vendored). | Wszystkie strony | Wersja niejasna, brak auto-update | Okreslic wersje, rozwazyc CDN |

### static/css/

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| `dashboard.css` | Style dashboardu: tabs, cards, charts, modal. 1012 LOC. | `dashboard.html` | Duplikacja zmiennych CSS | OK |
| `calendar.css` | Style standalone kalendarza. 728 LOC. | `calendar.html` | Duplikacja z dashboard.css | Rozwazyc usunięcie |
| `home.css` | Style legacy strony. 493 LOC. | `index.html` | Uzywane tylko przez legacy page | Usunac z prod jesli legacy usuniety |

### .github/workflows/

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| `deploy.yml` | Auto-deploy na Cloud Run. Push to main. | GH Secrets, Cloud Run | Brak testow, brak staging, brakujace env vars | Dodac testy, env vars |
| `security-scan.yml` | Daily security scan: Gitleaks + Safety + pip-audit. | requirements.txt | continue-on-error:true ignoruje bledy | Usunac continue-on-error |

### scripts/security/

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| `scan_secrets.sh` | Uruchom Gitleaks lokalnie lub via Docker. | .pre-commit-config.yaml | Brak | OK |
| `security_audit.sh` | Skrypt audytu bezpieczenstwa. | - | Nie przeczytany | Sprawdzic zawartosc |
| `validate_env.sh` | Walidacja pliku .env. | .env | Nie przeczytany | Sprawdzic zawartosc |

### tests/

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| `security_tests.py` | Testy IDOR + headers. 131 LOC. | app.py, database.py | Wymagaja dzialajacego serwera | Dodac Flask test client |

### design-showcase/

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| ~~`index.html`~~ | ~~Indeks prototypow~~ | - | ~~Martwy kod w repo~~ | USUNIETO (2026-04-06) |
| ~~`statistics-v2-*.html`~~ | ~~4 warianty nowego designu statystyk~~ | - | ~~Martwy kod~~ | USUNIETO (2026-04-06) |
| ~~`variant-*.html`~~ | ~~4 warianty designu~~ | - | ~~Martwy kod~~ | USUNIETO (2026-04-06) |

### stats-dashboard/ (React)

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| `src/App.tsx` | Entry point - renderuje StatisticsPage | - | Nie zintegrowany z Flask | Okreslic plan |
| `src/pages/StatisticsPage.tsx` | Strona statystyk | components/* | Prototyp, moze byc nieaktualny | Okreslic plan |
| `src/components/charts/*.tsx` | 4 komponenty chart | StatisticsPage | Prototyp | Okreslic plan |
| `src/components/statistics/*.tsx` | 3 komponenty stats | StatisticsPage | Prototyp | Okreslic plan |
| `src/components/ui/*.tsx` | 2 UI komponenty | Wszystkie | Prototyp | Okreslic plan |
| `package.json` | Zaleznosci: React 19, Vite 7, Tailwind 4 | node_modules | Nowoczesny stack, ale nieuzywany | Okreslic plan |

### .idea/ (IntelliJ)

| Sciezka | Rola | Powiazania | Ryzyka | Rekomendacje |
|---------|------|------------|--------|--------------|
| ~~Caly folder~~ | ~~Konfig IDE IntelliJ~~ | - | ~~Lokalne sciezki, szum w repo~~ | USUNIETO (2026-04-06) |

---

## Pliki Krytyczne

1. **app.py** - Serce aplikacji. Kazda zmiana tu wplywa na caly system.
2. **database.py** - Warstwa danych. Blad tu = utrata/uszkodzenie danych.
3. `.env` - Realne credentials. Nie commitowac.
4. `Dockerfile` + `.dockerignore` - Okreslaja co trafia do produkcji.
5. `.github/workflows/deploy.yml` - Auto-deploy. Blad = deploy zepsutej wersji.

## Pliki Martwe — USUNIETE (2026-04-06)

1. ~~`dashboard_old.html`~~ - USUNIETO
2. ~~`response.html`~~ - USUNIETO
3. ~~`design-showcase/`~~ - 9 plikow USUNIETYCH
4. ~~`.idea/`~~ - pliki IDE USUNIETE
