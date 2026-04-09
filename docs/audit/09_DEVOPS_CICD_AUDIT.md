# 09 - DEVOPS / CI-CD AUDIT

**Agent:** DEVOPS / CI-CD / KONFIG / OPERACJE  
**Data:** 2026-04-04

---

## Infrastruktura

| Komponent | Technologia | Status |
|-----------|------------|--------|
| Hosting | Google Cloud Run | Aktywny |
| Baza danych | Google Cloud Firestore | Aktywny |
| CI/CD | GitHub Actions | 2 workflows |
| Konteneryzacja | Docker (python:3.12-alpine) | Dockerfile w repo |
| Monitoring | - | BRAK |
| Logging | print() | Brak structured logging |
| Secrets management | Env vars + GH Secrets | Podstawowy |

---

## Findings

### OPS-01: `.dockerignore` nie wyklucza `.env` - KRYTYCZNE
- **Severity:** Critical
- **Lokalizacja:** `.dockerignore`
- **Opis:** Aktualna zawartosc `.dockerignore`:
  ```
  Dockerfile
  README.md
  *.pyc
  *.pyo
  *.pyd
  __pycache__
  .pytest_cache
  venv
  .venv
  .git
  .gitignore
  uruchom.bat
  setup_server.sh
  ```
  BRAK: `.env`, `.env.*`, `*.env`, `.idea/`, `design-showcase/`, `dashboard_old.html`, `response.html`, `tests/`, `scripts/`, `stats-dashboard/`, `zmiany.md`, `AUDIT/`
- **Wplyw:** `COPY . ./` w Dockerfile skopiuje `.env` do obrazu jesli plik istnieje na dysku. Obraz z credentials moze trafic do rejestru.
- **Rekomendacja:** Dodac do `.dockerignore`:
  ```
  .env
  .env.*
  *.env
  .idea/
  design-showcase/
  dashboard_old.html
  response.html
  tests/
  scripts/
  stats-dashboard/
  AUDIT/
  zmiany.md
  *.md
  !README.md
  ```
- **Status:** FIXED (2026-04-06) — .env, .env.*, *.env, .idea/, design-showcase/, AUDIT/, .planning/, .claude/, tests/, scripts/, stats-dashboard/ dodane

### OPS-02: Deploy workflow nie ustawia env vars produkcyjnych
- **Severity:** High
- **Lokalizacja:** `.github/workflows/deploy.yml:35-36`
- **Opis:** Workflow ustawia TYLKO `SECRET_KEY`:
  ```yaml
  env_vars: |
    SECRET_KEY=${{ secrets.SECRET_KEY }}
  ```
  Brak: `GYM_EMAIL`, `GYM_PASSWORD`, `GYM_URL`, `ADMIN_SECRET`, `ADMIN_PASSWORD`.
- **Wplyw:** Te env vars musza byc ustawione recznie w Cloud Run Console. Jesli ktos zrobi nowy deploy z `--clear-env-vars`, aplikacja przestanie dzialac.
- **Rekomendacja:** Dodac wszystkie wymagane env vars do workflow (jako GH secrets):
  ```yaml
  env_vars: |
    SECRET_KEY=${{ secrets.SECRET_KEY }}
    GYM_URL=${{ secrets.GYM_URL }}
    GYM_EMAIL=${{ secrets.GYM_EMAIL }}
    GYM_PASSWORD=${{ secrets.GYM_PASSWORD }}
    ADMIN_SECRET=${{ secrets.ADMIN_SECRET }}
  ```
- **Status:** proposed

### OPS-03: Brak staging/test environment
- **Severity:** High
- **Lokalizacja:** `.github/workflows/deploy.yml`
- **Opis:** Kazdy push do `main` deployuje bezposrednio na produkcje. Brak staging environment, brak testow przed deploy, brak canary releases.
- **Wplyw:** Kazdy bled trafia bezposrednio do uzytkownikow.
- **Rekomendacja:** (a) Dodac branch `staging` z oddzielnym Cloud Run service, (b) dodac testy do CI przed deploy.
- **Effort:** Medium | **Impact:** High

### OPS-04: Health check nie sprawdza Firestore
- **Severity:** Medium
- **Lokalizacja:** `app.py:945-948`
- **Opis:**
  ```python
  @app.route('/health')
  def health():
      return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
  ```
  Endpoint zwraca "healthy" nawet jesli Firestore jest niedostepny.
- **Wplyw:** Cloud Run moze routowac traffic do instancji bez polaczenia z baza danych.
- **Rekomendacja:** Dodac probe Firestore w health check:
  ```python
  try:
      database.get_db().collection('daily_entries').limit(1).get()
      return jsonify({'status': 'healthy', 'firestore': 'connected'})
  except:
      return jsonify({'status': 'degraded', 'firestore': 'disconnected'}), 503
  ```
- **Effort:** Low | **Impact:** Medium

### OPS-05: Gunicorn z 1 worker i 8 threads
- **Severity:** Medium
- **Lokalizacja:** `Dockerfile:20`
- **Opis:** `CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app`
  - `--workers 1`: Pojedynczy proces. Jesli utknie (deadlock, OOM), caly kontener jest nieosiagalny.
  - `--timeout 0`: Brak timeout. Worker moze wisiec w nieskonczonosc (np. eFitness nie odpowiada).
- **Wplyw:** Ryzyko zawieszenia sie kontenera.
- **Rekomendacja:** Dodac `--timeout 120` (2 min). Dla Cloud Run `--timeout 0` jest akceptowalny bo Cloud Run sam zarzadza lifecycle, ale warto miec guard.
- **Effort:** Low | **Impact:** Medium

### OPS-06: Brak structured logging
- **Severity:** Medium
- **Lokalizacja:** Caly `app.py` i `database.py`
- **Opis:** Logging oparty na `print()` zamiast `logging` module. `database.py` uzywa `logger = logging.getLogger(__name__)` ale `app.py` uzywa `print()`. Niespojne.
- **Wplyw:** Trudne debugowanie na Cloud Run. Brak leveli (INFO/WARNING/ERROR). Brak structured JSON logs.
- **Rekomendacja:** Zastapic `print()` w `app.py` loggerem. Skonfigurowac JSON format dla Cloud Run.
- **Effort:** Low | **Impact:** Medium

### OPS-07: Security scan pipeline uzywa `continue-on-error: true`
- **Severity:** Low
- **Lokalizacja:** `.github/workflows/security-scan.yml:33-41`
- **Opis:** Safety i pip-audit maja `continue-on-error: true`. Pipeline zawsze przechodzi nawet z podatnosciami.
- **Wplyw:** Znane podatnosci nie blokuja merge/deploy.
- **Rekomendacja:** Usunac `continue-on-error` i naprawic znalezione podatnosci.
- **Effort:** Low | **Impact:** Medium

### OPS-08: Brak backup/recovery strategy
- **Severity:** Low
- **Lokalizacja:** Caly projekt
- **Opis:** Aplikacja oferuje `/api/export/full` ale brak automatycznego backup Firestore. Brak udokumentowanej procedury recovery.
- **Wplyw:** Utrata danych przy bledzie Firestore lub przypadkowym usunieciu.
- **Rekomendacja:** Wlaczyc Firestore automated backups. Udokumentowac procedure recovery.
- **Effort:** Low | **Impact:** Medium

### OPS-09: `.idea/` folder w repo
- **Severity:** Low
- **Lokalizacja:** `.idea/`
- **Opis:** Pliki konfiguracyjne IntelliJ IDEA commitowane do repo. Zawieraja lokalne sciezki i konfiguracje.
- **Wplyw:** Szum w repo. Potencjalnie ujawniaja lokalne sciezki.
- **Rekomendacja:** Dodac `.idea/` do `.gitignore` i usunac z repo.
- **Effort:** Low | **Impact:** Low

### OPS-10: `setup_server.sh` - brak HTTPS
- **Severity:** Info
- **Lokalizacja:** `setup_server.sh`
- **Opis:** Skrypt instaluje gunicorn na porcie 5000 bez SSL/TLS. Brak konfiguracji reverse proxy (nginx) z HTTPS.
- **Wplyw:** Ruch HTTP nieszyfrowany na serwerze VPS.
- **Rekomendacja:** Dodac instrukcje dla nginx + certbot w README lub rozszerzyc skrypt.
- **Effort:** Medium | **Impact:** Low
