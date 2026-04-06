# 05 - FRONTEND AUDIT

**Agent:** FRONTEND / UI ENGINEERING  
**Data:** 2026-04-04

---

## Findings

### FE-01: Trzy oddzielne strony z powielona logika
- **Severity:** High
- **Lokalizacja:** `templates/index.html`, `templates/dashboard.html`, `templates/calendar.html`
- **Opis:** Trzy niezalezne HTML pages z wlasnymi stylami CSS i logiką JS. Brak wspoldzielenia komponentow (header, theme, auth). Kazda strona ładuje Google Fonts i DOMPurify osobno.
- **Wplyw:** Duplikacja ~300 LOC CSS (CSS variables, base styles). Zmiana motywu wymaga edycji 3 plikow. Niespojne wartosci CSS variables miedzy stronami.
- **Rekomendacja:** Stworzyc base template (Jinja2 extends/blocks) z wspolnym header, CSS vars, auth logic.
- **Effort:** Medium | **Impact:** High

### FE-02: `index.html` ma inline JS (852 LOC)
- **Severity:** High
- **Lokalizacja:** `templates/index.html:611-850`
- **Opis:** Legacy strona glowna ma caly JS inline w `<script>` bloku (~240 LOC). Jest to sprzeczne z celem usunięcia `unsafe-inline` z CSP (opisanym w zmiany.md).
- **Wplyw:** Blokuje usuniecie `unsafe-inline` z CSP.
- **Rekomendacja:** Zakończyć migrację: wyniesc caly inline JS do `static/js/home.js` (ktory juz istnieje ale jest niepelny).
- **Effort:** Medium | **Impact:** High

### FE-03: Niespojne CSS variables miedzy stronami
- **Severity:** Medium
- **Lokalizacja:**
  - `dashboard.html`: `--bg-dark: #0a0a12`, `--primary: #7c3aed`
  - `index.html`: `--bg-dark: #0f0f1a`, `--primary: #6366f1`
  - `calendar.html`: `--bg-dark: #0c0c14`, `--primary: #7c3aed`
- **Opis:** Kazda strona ma inne wartosci CSS variables. Rozne kolory tla, rozne primary colors.
- **Wplyw:** Niespojne doswiadczenie wizualne miedzy stronami.
- **Rekomendacja:** Ujednolicic w jednym `static/css/variables.css` importowanym przez wszystkie strony.
- **Effort:** Low | **Impact:** Medium

### FE-04: Inline styles w dashboard.html
- **Severity:** Medium
- **Lokalizacja:** `templates/dashboard.html:218-253, 294-370`
- **Opis:** Wiele elementow ma rozbudowane inline style (`style="display: flex; gap: 8px; margin-bottom: 16px; overflow-x: auto;..."`). Pomimo ze glowny CSS jest w pliku, sekcje statystyk i New Year Effect uzywaja inline.
- **Wplyw:** Trudne do utrzymania, niemozliwe do nadpisania w media queries, blokuje strict CSP (style-src).
- **Rekomendacja:** Przeniesc inline styles do klas CSS w `dashboard.css`.
- **Effort:** Medium | **Impact:** Medium

### FE-05: `renderBodyPartsGrid()` tworzy elementy programatycznie z inline styles
- **Severity:** Medium
- **Lokalizacja:** `static/js/dashboard.js:465-569`
- **Opis:** Caly modal workout jest tworzony programatycznie z `createElement()` i `style.cssText`. Styl kazego elementu jest definiowany w JS stringach, nie w CSS.
- **Wplyw:** ~100 LOC ciezkich do utrzymania. Brak mozliwosci responsive design przez media queries. Brak hover states.
- **Rekomendacja:** Uzyc klas CSS zamiast inline styles w JS.
- **Effort:** Medium | **Impact:** Medium

### FE-06: Brak error boundary / global error handler
- **Severity:** Medium
- **Lokalizacja:** Caly frontend
- **Opis:** Bledy JS (np. `TypeError: Cannot read property of null`) sa łapane tylko lokalnie w try/catch. Brak globalnego handlera dla uncaught exceptions.
- **Wplyw:** Uzytkownik widzi zamrozoną stronie bez informacji o bledzie.
- **Rekomendacja:** Dodac `window.onerror` handler z UI fallback.
- **Effort:** Low | **Impact:** Medium

### FE-07: `safeSanitize()` uzywana niespojnie
- **Severity:** Low
- **Lokalizacja:** `static/js/dashboard.js`
- **Opis:** Niektore `innerHTML` uzycia sa opakowane w `safeSanitize()`, ale nie wszystkie. Np. `renderBestWorstTimes()` linie 1084-1106 uzywa surowego `innerHTML` bez sanityzacji.
- **Wplyw:** Niespojne zabezpieczenie. Dane z API (np. `t.label`) renderowane bez sanityzacji.
- **Rekomendacja:** Konsekwentnie uzywac `safeSanitize()` LUB przejsc na `textContent` + `createElement()`.
- **Status:** PARTIALLY FIXED (2026-04-06) — fallback safeSanitize teraz stripuje HTML zamiast zwracac raw. Nadal niektorych `innerHTML` uzywa bez `safeSanitize()`.
- **Effort:** Low | **Impact:** Low

### FE-08: Magiczne stalej w JS
- **Severity:** Low
- **Lokalizacja:** `static/js/dashboard.js:35-36`
- **Opis:** `const CACHE_TTL = 60000;` i `const REFRESH_COOLDOWN_MS = 30000;` - ok, ale potem `setInterval(fetchLiveCount, 60000)` (linia 239), `setInterval(fetchData, 30000)` (index.html:768) - stalej nie uzywane.
- **Wplyw:** Niespojnosc, trudne do konfiguracji.
- **Rekomendacja:** Uzyc stalych zamiast magic numbers.
- **Effort:** Low | **Impact:** Low

### FE-09: Brak loading states na kartach
- **Severity:** Low
- **Lokalizacja:** Dashboard tabs
- **Opis:** Przy pierwszym ladowaniu zakladki "Statystyki" lub "Sila" widac "Ladowanie..." jako tekst, ale brak skeleton loaderow lub spinnerow.
- **Wplyw:** UX - uzytkownik nie wie ile bedzie czekal.
- **Rekomendacja:** Dodac skeleton loaders lub animowane spinnery.
- **Effort:** Low | **Impact:** Low

### FE-10: SVG progression chart - fixed width assumption
- **Severity:** Low
- **Lokalizacja:** `static/js/dashboard.js:1393-1452`
- **Opis:** `const chartWidth = container.offsetWidth || 300;` - jesli container nie jest jeszcze widoczny (tab ukryty), offsetWidth = 0, fallback = 300px.
- **Wplyw:** Chart moze byc zle wyrenderowany jesli zakladka "Sila" jest ladowana w tle.
- **Rekomendacja:** Przerysowac chart przy aktywacji zakladki.
- **Effort:** Low | **Impact:** Low

### FE-11: `downloadBackup()` i `downloadWorkouts()` nie uzywaja admin secret
- **Severity:** Low
- **Lokalizacja:** `static/js/dashboard.js:1276-1296`
- **Opis:** Export endpointy wymagaja admin secret, ale frontend wywoluje je bez headera. Zawsze dostana 401.
- **Wplyw:** Funkcja "Pobierz backup" w UI nie dziala dla zwyklych uzytkownikow (poprawne zachowanie) ale takze nie dziala dla admina (bo brak headera).
- **Rekomendacja:** (a) Usunac przyciski backup z UI dla non-admin, LUB (b) dodac admin panel z polem na secret.
- **Effort:** Low | **Impact:** Low

### FE-12: `calendar.html` - standalone z duplikacja auth
- **Severity:** Info
- **Lokalizacja:** `templates/calendar.html`, `static/js/calendar.js`
- **Opis:** Osobna strona z wlasna logika auth (ale uzywa tego samego `/api/auth/me`). Duplikuje styl i theme z dashboard. Teraz dashboard.html ma wbudowany kalendarz, wiec standalone calendar jest redundantny.
- **Wplyw:** Legacy page.
- **Rekomendacja:** Rozwazyc usuniecie i redirect `/calendar` -> `/?tab=calendar`.
- **Effort:** Low | **Impact:** Info
