# 12 - RECOMMENDED PATCHES

**Agent:** ORCHESTRATOR / SECURITY  
**Data:** 2026-04-04

---

## Patche Wymagajace Recznej Decyzji

Te zmiany sa zbyt ryzykowne lub nieodwracalne do automatycznego wdrozenia.

---

### PATCH-01: Rotacja ADMIN_SECRET i SECRET_KEY

- **Powod:** Obecne wartosci w `.env` moga byc znane osobom z dostepem do maszyny deweloperskiej.
- **Kroki:**
  1. Wygenerowac nowy ADMIN_SECRET: `openssl rand -hex 32`
  2. Wygenerowac nowy SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`
  3. Zaktualizowac w Cloud Run Console (env vars)
  4. Zaktualizowac w GitHub Secrets (SECRET_KEY)
  5. Zaktualizowac w lokalnym `.env`
  6. Zrestartowac Cloud Run service
- **Rollback:** Przywrocic stare wartosci w Cloud Run Console
- **Ryzyko:** Wszystkie aktywne sesje uzytkownikow zostana uniewaznione (SECRET_KEY zmieniony)
- **Wymaga zgody:** TAK

### PATCH-02: Zmiana hasla GYM_PASSWORD

- **Powod:** Haslo widoczne w `.env` na dysku. Jesli ktokolwiek mial dostep do maszyny, haslo jest skompromitowane.
- **Kroki:**
  1. Zalogowac sie na portal eFitness
  2. Zmienic haslo w portalu
  3. Zaktualizowac w Cloud Run Console
  4. Zaktualizowac w lokalnym `.env`
  5. Zweryfikowac ze scraper dziala (`/api/occupancy`)
- **Rollback:** Przywrocic stare haslo w portalu eFitness
- **Ryzyko:** Jesli nowe haslo nie zadziala, scraper przestanie zbierac dane
- **Wymaga zgody:** TAK

### PATCH-03: Wymuszenie zmiany hasel uzytkownikow

- **Powod:** Po wzmocnieniu polityki hasel (SEC-02), istniejace konta moga miec slabe hasla.
- **Kroki:**
  1. Wdrozyc nowa politykę hasel
  2. Dodac flage `must_change_password` w user document
  3. Na login sprawdzic czy haslo spelnia nowa politykę
  4. Jesli nie - wymusic zmiane (redirect do formularza zmiany hasla)
- **Rollback:** Usunac flage `must_change_password`
- **Ryzyko:** Uzytkownicy nie moga sie zalogowac dopoki nie zmienia hasla
- **Wymaga zgody:** TAK

### PATCH-04: Wlaczenie Cloud Run authentication

- **Powod:** Obecna konfiguracja `--allow-unauthenticated` pozwala kazdemu na dostep do endpointow.
- **Kroki:**
  1. Ocenic czy dashboard powinien byc publiczny czy za auth
  2. Jesli za auth: usunac `--allow-unauthenticated` z deploy.yml
  3. Skonfigurowac IAP (Identity-Aware Proxy) lub Cloud Run auth
  4. Dodac wyjatek dla `/health`
- **Rollback:** Dodac z powrotem `--allow-unauthenticated`
- **Ryzyko:** Wszystkie linki do aplikacji przestana dzialac bez auth
- **Wymaga zgody:** TAK

### PATCH-05: Migracja stats-dashboard (React)

- **Powod:** Nieuzywany prototyp React w repo. Trzeba zdecydowac o przyszlosci.
- **Opcje:**
  - **A) Zintegrować:** Skonfigurowac Vite proxy, budowac do `static/`, serwowac z Flask
  - **B) Oddzielny hosting:** Deploy na Vercel/Netlify, polaczenie z API
  - **C) Usunac:** Wyczysc repo jesli React nie jest planowany
- **Rollback:** N/A (zalezy od opcji)
- **Ryzyko:** Zalezy od wybranej opcji
- **Wymaga zgody:** TAK

---

## Kolejnosc Wdrazania (rekomendowana)

```
1. PATCH-01 (rotacja secrets)  ← NAJPIERW, bo warunkuje bezpieczeństwo
   ↓
2. Zmiany auto-approve z 11_APPLIED_FIXES_CHANGELOG.md (Zmiany 1-10)  ← DONE (2026-04-06)
   ↓
3. PATCH-02 (zmiana hasla gym)  ← po weryfikacji ze scraper dziala
   ↓
4. PATCH-03 (wymuszenie zmiany hasel) ← po wdrozeniu nowej polityki (POLITYKA WDROZONA)
   ↓
5. PATCH-04 (Cloud Run auth) ← opcjonalne, zalezy od wymagań
   ↓
6. PATCH-05 (React migration) ← strategiczna decyzja
```

> **Update 2026-04-06:** Krok 2 zrealizowany — 10 zmian auto-approve wdrozonych. Nowa polityka hasel (krok 4 prereq) wdrozona. Pozostaja PATCH-01 do PATCH-05 wymagajace recznej decyzji.

---

## Monitoring Po Wdrozeniu

Po kazdym patchu zweryfikowac:
- [ ] `/health` zwraca 200
- [ ] `/api/occupancy` zwraca dane
- [ ] Login/register dziala
- [ ] Kalendarz zapisuje treningi
- [ ] Statystyki sie laduja
- [ ] Scraper zbiera dane (sprawdzic po 5 minutach)
