# 01 - REPO MAP & STACK TECHNOLOGICZNY

**Agent:** REPO MAPPER / ARCHITEKTURA  
**Data:** 2026-04-04

---

## Stack Technologiczny

| Warstwa | Technologia | Wersja |
|---------|------------|--------|
| Backend | Python | 3.12 |
| Framework | Flask | >=3.1.0 |
| Baza danych | Google Cloud Firestore | >=2.19.0 |
| Serwer WSGI | Gunicorn | >=23.0.0 |
| Konteneryzacja | Docker (Alpine) | python:3.12-alpine |
| Hosting | Google Cloud Run | - |
| CI/CD | GitHub Actions | v4 |
| Frontend (legacy) | Vanilla JS + DOMPurify | - |
| Frontend (nowy) | React 19 + TypeScript + Vite 7 + Tailwind 4 | stats-dashboard/ |
| Limiter | flask-limiter | >=3.8.0 |
| Kompresja | flask-compress | >=1.17 |
| Scraping | requests + BeautifulSoup4 | >=2.32.4 / >=4.12.3 |
| Hashing hasel | bcrypt | >=4.2.0 |
| Timezone | pytz | >=2024.2 |

---

## Struktura Katalogow

```
gym-tracker/
├── .dockerignore              # Docker ignore rules (BRAK .env!)
├── .env                       # REALNE dane logowania (NIE w git)
├── .env.example               # Szablon zmiennych srodowiskowych
├── .github/
│   └── workflows/
│       ├── deploy.yml         # Auto-deploy na Cloud Run
│       └── security-scan.yml  # Skanowanie bezpieczenstwa
├── .gitignore                 # Git ignore (ma .env)
├── .idea/                     # IntelliJ IDE config (NIE powinno byc w repo)
│   ├── .gitignore
│   ├── caches/
│   ├── deviceManager.xml
│   ├── gym-tracker.iml
│   ├── libraries/
│   ├── markdown.xml
│   ├── misc.xml
│   ├── modules.xml
│   ├── vcs.xml
│   └── workspace.xml
├── .pre-commit-config.yaml    # Pre-commit hooks (Gitleaks + basic)
├── app.py                     # Glowny serwer Flask (1012 LOC)
├── dashboard_old.html         # DEAD FILE - stary dashboard
├── database.py                # Warstwa Firestore (2060 LOC)
├── design-showcase/           # Prototypy UI (nie uzywane w prod)
│   ├── index.html
│   ├── statistics-v2-real-data-glass.html
│   ├── statistics-v2-real-data-pro.html
│   ├── statistics-v2-variant-1.html
│   ├── statistics-v2-variant-2.html
│   ├── variant-a-bento.html
│   ├── variant-b-dashboard.html
│   ├── variant-c-minimal.html
│   └── variant-current.html
├── Dockerfile                 # Obraz Docker (Alpine)
├── LICENSE                    # MIT License
├── README.md                  # Dokumentacja projektu
├── requirements.txt           # Zaleznosci Python
├── response.html              # DEAD FILE - stara wersja strony
├── scripts/
│   └── security/
│       ├── scan_secrets.sh    # Skrypt Gitleaks
│       ├── security_audit.sh  # Skrypt audytu
│       └── validate_env.sh    # Walidacja .env
├── SECURITY.md                # Polityka bezpieczenstwa
├── setup_server.sh            # Instalacja na serwerze Linux
├── static/
│   ├── css/
│   │   ├── calendar.css       # Style kalendarza (728 LOC)
│   │   ├── dashboard.css      # Style dashboardu (1012 LOC)
│   │   └── home.css           # Style legacy strony (493 LOC)
│   └── js/
│       ├── calendar.js        # Logika kalendarza (583 LOC)
│       ├── dashboard.js       # Logika glowna dashboardu (1457 LOC)
│       ├── home.js            # Logika legacy strony (253 LOC)
│       └── purify.min.js      # DOMPurify (vendored)
├── stats-dashboard/           # PROTOTYP - React dashboard
│   ├── eslint.config.js
│   ├── index.html
│   ├── node_modules/          # (nie commitowane)
│   ├── package.json
│   ├── package-lock.json
│   ├── public/
│   ├── README.md
│   ├── src/
│   │   ├── App.css
│   │   ├── App.tsx
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── DailyChart.tsx
│   │   │   │   ├── HourlyChart.tsx
│   │   │   │   ├── WeeklyChart.tsx
│   │   │   │   └── YearlyHeatmap.tsx
│   │   │   ├── layout/
│   │   │   │   └── FloatingDock.tsx
│   │   │   ├── statistics/
│   │   │   │   ├── BestWorstTimes.tsx
│   │   │   │   ├── MonthComparison.tsx
│   │   │   │   └── NewYearEffect.tsx
│   │   │   └── ui/
│   │   │       ├── Card.tsx
│   │   │       └── StatsCard.tsx
│   │   ├── index.css
│   │   ├── lib/
│   │   │   └── utils.ts
│   │   ├── main.tsx
│   │   └── pages/
│   │       └── StatisticsPage.tsx
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── templates/
│   ├── calendar.html          # Standalone kalendarz (1433 LOC)
│   ├── dashboard.html         # Glowny dashboard (541 LOC)
│   └── index.html             # Legacy strona glowna (852 LOC)
├── tests/
│   └── security_tests.py     # Testy bezpieczenstwa IDOR (131 LOC)
├── uruchom.bat                # Windows batch starter
└── zmiany.md                  # Changelog zmian (57 LOC)
```

---

## Entry Points Aplikacji

| Entry Point | Plik | Opis |
|-------------|------|------|
| Serwer Flask | `app.py:1002-1009` | `app.run()` lub `gunicorn app:app` |
| Dashboard | `app.py:270-273` | `GET /` -> `dashboard.html` |
| Legacy page | `app.py:276-279` | `GET /legacy` -> `index.html` |
| Calendar | `app.py:361-364` | `GET /calendar` -> `calendar.html` |
| API base | `app.py:282+` | `/api/*` endpointy |
| Background updater | `app.py:258-267` | Thread demoniczny - fetch co 3 min |
| Docker | `Dockerfile` | `gunicorn --bind :$PORT` |
| CI/CD | `.github/workflows/deploy.yml` | Push to main -> Cloud Run |

---

## Krytyczne Flow Aplikacji

### 1. Scraping oblozenenia silowni
```
Background Thread (co 3 min) -> get_gym_session() -> POST login do eFitness
  -> GET /na-terenie-klubu -> parse HTML (BeautifulSoup) -> regex
  -> entries_cache (in-memory dict) -> save_to_firestore()
```

### 2. Rejestracja/Logowanie uzytkownika
```
POST /api/auth/register -> validate_username/password -> check unique
  -> hash_password(bcrypt) -> Firestore users collection
  -> Flask session (server-side cookie)
```

### 3. Zapis treningu
```
POST /api/workout -> require_login() -> validate date + body_parts
  -> database.save_workout(user_id from session)
  -> Firestore workouts/{user_id}_{date}
```

### 4. Statystyki oblozenenia
```
GET /api/analytics/extended -> fetch_recent_hourly_data(30 days)
  -> get_daily_averages() + get_hourly_averages() + best/worst combos
  -> All computed in Python from raw Firestore data
```

---

## Zaleznosci Miedzy Modulami

```
app.py
  ├── imports: database.py (Firestore operations)
  ├── imports: flask, flask_cors, flask_limiter, flask_compress
  ├── imports: requests, bs4 (scraping)
  ├── imports: threading (background updater)
  └── serves: templates/*.html + static/*

database.py
  ├── imports: google.cloud.firestore
  ├── imports: bcrypt (password hashing)
  └── standalone module (no app.py dependency)

templates/dashboard.html
  └── loads: static/js/dashboard.js, static/css/dashboard.css, static/js/purify.min.js

templates/index.html
  └── loads: static/js/home.js, static/css/home.css, static/js/purify.min.js (inline JS too)

templates/calendar.html
  └── loads: static/js/calendar.js, static/css/calendar.css (standalone page)

stats-dashboard/ (IZOLOWANY - nie zintegrowany z Flask)
  └── standalone React app, brak polaczenia z backendem
```

---

## Pliki Martwe / Do Usuniecia

| Plik | Powod |
|------|-------|
| `dashboard_old.html` | Stary dashboard, zastapiony przez templates/dashboard.html |
| `response.html` | Kolejna stara wersja strony glownej |
| `design-showcase/` | 9 plikow HTML - prototypy UI, nie uzywane |
| `.idea/` | Pliki IDE IntelliJ - nie powinny byc w repo |
| `static/css/home.css` | Uzywany tylko przez legacy index.html |
| `static/js/home.js` | Uzywany tylko przez legacy index.html |
| `uruchom.bat` | Windows batch file - niszowy use case |
