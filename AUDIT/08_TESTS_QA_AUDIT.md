# 08 - TESTS & QA AUDIT

**Agent:** QA / TESTY / NIEZAWODNOSC  
**Data:** 2026-04-04

---

## Stan Testow

| Metryka | Wartosc |
|---------|---------|
| Pliki testowe | 1 (`tests/security_tests.py`) |
| Testy jednostkowe | 0 |
| Testy integracyjne | 3 (IDOR + headers) |
| Testy E2E | 0 |
| Testy frontend | 0 |
| Pokrycie kodu | ~2% (tylko auth + IDOR flow) |
| Framework testowy | unittest (Python stdlib) |

---

## Findings

### QA-01: Brak unit testow dla logiki biznesowej
- **Severity:** High
- **Lokalizacja:** `database.py` (2060 LOC bez testow)
- **Opis:** Zadna z 30+ funkcji w database.py nie ma unit testow. Kluczowe funkcje bez testow:
  - `validate_username()` / `validate_password()` - walidacja danych
  - `is_complete_day()` - logika wykrywania swiat/wczesnych zamkniec
  - `get_hourly_averages()` - zlozony algorytm obliczen
  - `get_month_comparison()` - logika porownania miesiecy
  - `get_new_year_effect()` - zlozony algorytm statystyk
- **Wplyw:** Brak pewnosci ze logika dziala poprawnie. Regresje odkrywane dopiero na produkcji.
- **Rekomendacja:** Napisac unit testy dla: walidacji, `is_complete_day()`, `get_hourly_averages()`, `get_month_comparison()`.
- **Effort:** Medium | **Impact:** High

### QA-02: Brak testow frontendu
- **Severity:** High
- **Lokalizacja:** `static/js/*.js`
- **Opis:** 2293 LOC JavaScript bez zadnego testu. Kluczowe flow bez testow:
  - Auth flow (login/register/logout)
  - Kalendarz (renderowanie, nawigacja, zapis)
  - Wykresy (renderowanie z danymi, edge cases)
  - Modal workout (toggle parts, weight data, save)
- **Wplyw:** Frontend bugs wykrywane reczne.
- **Rekomendacja:** Minimum: testy dla auth flow i workout CRUD (np. z Playwright lub Cypress).
- **Effort:** High | **Impact:** Medium

### QA-03: Istniejace testy wymagaja dzialajacego serwera
- **Severity:** Medium
- **Lokalizacja:** `tests/security_tests.py:8`
- **Opis:** `BASE_URL = "http://127.0.0.1:5000"` - testy wymagaja uruchomionego serwera Flask z Firestore. Nie moga byc uruchomione w CI bez infrastruktury.
- **Wplyw:** Testy nie sa czescia CI/CD pipeline. Uruchamiane tylko recznie.
- **Rekomendacja:** (a) Dodac Flask test client (`app.test_client()`), (b) mockować Firestore, (c) dodac do CI z Firestore emulator.
- **Effort:** Medium | **Impact:** Medium

### QA-04: Brak testow edge case'ow w `is_complete_day()`
- **Severity:** Medium
- **Lokalizacja:** `database.py:66-120`
- **Opis:** Zlozony algorytm z wieloma warunkami (4+ consecutive zeros, identical end values, missing hours). Zadne testy nie weryfikuja:
  - Pusta godzinowa mapa
  - Swieto z 0 wejsciami
  - Dzien z dokladnie 4 identycznymi wartosciami na koncu
  - Normalny pelny dzien
  - Weekend vs weekday
- **Wplyw:** Potencjalne bledne filtrowanie danych w statystykach.
- **Rekomendacja:** Napisac parametryzowane testy z roznymi scenariuszami.
- **Effort:** Low | **Impact:** Medium

### QA-05: Brak smoke testow dla kluczowych flow
- **Severity:** Medium
- **Lokalizacja:** Caly projekt
- **Opis:** Brak minimalnego zestawu testow ktory weryfikuje ze aplikacja startuje i glowne endpointy odpowiadaja.
- **Wplyw:** Deploy moze wdrozyc zepsuta wersje bez ostrzezenia.
- **Rekomendacja:** Dodac smoke test: start serwer -> GET / -> 200, GET /api/occupancy -> 200, POST /api/auth/login -> 200/401.
- **Effort:** Low | **Impact:** High

---

## Checklist Manualnego QA

### Flow 1: Rejestracja i Logowanie
- [ ] Otworz strone glowna - powinien pojawic sie modal logowania
- [ ] Kliknij "Zarejestruj sie" - formularz rejestracji
- [ ] Podaj nazwe < 3 znaki - powinien blad walidacji
- [ ] Podaj poprawne dane - powinno zalogowac i zamknac modal
- [ ] Odswierz strone - powinno byc nadal zalogowane (sesja)
- [ ] Kliknij badge uzytkownika -> potwierdz logout -> modal logowania
- [ ] Zaloguj sie istniejacym kontem

### Flow 2: Zapis Treningu
- [ ] Na zakladce Kalendarz kliknij dowolny dzien
- [ ] Modal "Dodaj trening" - kliknij partje ciala
- [ ] Wpisz kg/ser/powt
- [ ] Kliknij "Zapisz" - modal zamknie sie, dzien powinien miec ikony
- [ ] Kliknij ten sam dzien - modal "Edytuj trening" z danymi
- [ ] Odznacz partie, kliknij "Zapisz" z minimum 1 partie
- [ ] Sprawdz przycisk "Usun" - powinien usunac trening

### Flow 3: Statystyki
- [ ] Przejdz na zakladke "Statystyki"
- [ ] Sprawdz czy wykresy sie laduja (daily, hourly, weekly, heatmap)
- [ ] Sprawdz porownanie miesiecy (current vs previous)
- [ ] Sprawdz efekt noworoczny (moze nie byc danych)
- [ ] Nawiguj heatmape (strzalki rok)

### Flow 4: Sila
- [ ] Przejdz na zakladke "Sila"
- [ ] Sprawdz czy rekordy sie wyswietlaja (po dodaniu treningow z kg)
- [ ] Wybierz partie ciala z dropdown -> progresja
- [ ] Sprawdz czy wykres SVG renderuje sie poprawnie

### Flow 5: Mobile
- [ ] Otworz na telefonie (lub DevTools mobile)
- [ ] Sprawdz logowanie - modal responsywny?
- [ ] Sprawdz kalendarz - czy dni sie mieszcza?
- [ ] Sprawdz modal dodawania - inputy widoczne?
- [ ] Sprawdz scrollowanie w statystykach

### Flow 6: Error States
- [ ] Odłacz internet -> sprawdz komunikaty bledow
- [ ] Sprobuj GET /api/debug/day/invalid-date
- [ ] Sprobuj POST /api/workout z pustym body
- [ ] Sprobuj zalogowac sie z zlym haslem 10+ razy (rate limit)

---

## Rekomendowany Minimalny Zestaw Testow (do ETAPU 2)

### Python Unit Tests (pytest)
```
tests/
├── test_validation.py      # validate_username, validate_password
├── test_complete_day.py    # is_complete_day with parametrized scenarios
├── test_auth.py            # create_user, authenticate_user (with mock Firestore)
├── test_api.py             # Flask test client - key endpoints
└── conftest.py             # Fixtures: app, mock_firestore
```

### Smoke Tests (CI/CD)
```
tests/
└── test_smoke.py           # Start app, check /, /health, /api/occupancy
```
