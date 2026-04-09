# 06 - UI/UX & ACCESSIBILITY AUDIT

**Agent:** UI/UX / PRODUKT / DOSTEPNOSC  
**Data:** 2026-04-04

---

## Ogolna Ocena UX

Aplikacja ma dobry dark theme z czytelna hierarchia wizualna. Glowne flow (logowanie, dodawanie treningu, przegladanie statystyk) jest intuicyjne. Problemy dotycza glownie: braku feedbacku po akcjach, bledow dostepnosci, i niespojnosci miedzy stronami.

---

## Findings

### UX-01: Brak feedbacku po zapisaniu/usunieciu treningu
- **Severity:** High
- **Problem:** Po kliknieciu "Zapisz" w modalu trening zapisuje sie po cichu - modal zamyka sie, kalendarz sie odswiza, ale nie ma wizualnego potwierdzenia sukcesu.
- **Wplyw na uzytkownika:** Niepewnosc czy trening sie zapisal. Uzytkownik moze kliknac ponownie.
- **Proponowana zmiana:** Dodac toast notification "Trening zapisany!" (zielony) i "Trening usuniety" (czerwony) na 2-3 sekundy.
- **Priorytet:** High
- **Nadaje sie do ETAPU 2:** Tak

### UX-02: Brak walidacji w czasie rzeczywistym na formularzu logowania
- **Severity:** Medium
- **Problem:** Uzytkownik dowiaduje sie o bledzie dopiero po wyslaniu formularza. Brak wizualnych wskazowek o wymaganiach (min. dlugosci hasla, dozwolone znaki).
- **Wplyw na uzytkownika:** Frustracja przy rejestracji. Komunikaty bledow sa po angielsku ("Password must be at least 3 characters") mimo ze UI jest po polsku.
- **Proponowana zmiana:** (a) Przetlumaczyc bledy na polski, (b) dodac inline validation, (c) pokazac requirements pod polem.
- **Priorytet:** Medium
- **Nadaje sie do ETAPU 2:** Tak

### UX-03: Przycisk logout - brak wizualnego odroznienia
- **Severity:** Medium
- **Problem:** `<div class="user-badge" onclick="logout()">👤 ---</div>` - badge uzytkownika jest jednoczesnie przyciskiem logout. Brak ikony logout, brak vizualnego hint.
- **Wplyw na uzytkownika:** Nieoczywiste ze klikniecie wyloguje. Przypadkowe wylogowanie.
- **Proponowana zmiana:** Dodac osobny przycisk/ikone logout lub dropdown z opcjami.
- **Priorytet:** Medium
- **Nadaje sie do ETAPU 2:** Tak

### UX-04: Scroll horyzontalny w sekcji statystyk na mobile
- **Severity:** Medium
- **Problem:** Quick stats row (linia 218-253 w dashboard.html) uzywa `overflow-x: auto` z `min-width: 100px` na kazdym boxie. Na wazkim telefonie karty moga wychodzic poza ekran.
- **Wplyw na uzytkownika:** Uzytkownik moze nie wiedziec ze trzeba scrollować w prawo.
- **Proponowana zmiana:** Uzyc grid 2x2 na mobile zamiast horizontal scroll.
- **Priorytet:** Medium
- **Nadaje sie do ETAPU 2:** Tak

### UX-05: Brak stanu pustego (empty state) dla nowych uzytkownikow
- **Severity:** Medium
- **Problem:** Nowy uzytkownik widzi: "0" we wszystkich statystykach, pusty kalendarz, puste wykresy. Brak onboardingu lub wizualnej wskazowki co robic.
- **Wplyw na uzytkownika:** Dezorientacja. Nie wiadomo od czego zaczac.
- **Proponowana zmiana:** Dodac empty state z CTA: "Kliknij na dzisiejszy dzien aby dodac pierwszy trening!".
- **Priorytet:** Medium
- **Nadaje sie do ETAPU 2:** Tak

### UX-06: Heatmapa roczna - male komorki na mobile
- **Severity:** Low
- **Problem:** 12 miesiecy x ~31 dni = setki malych kwadracikow. Na mobile sa tak male ze nie da sie ich kliknac ani odczytac.
- **Wplyw na uzytkownika:** Heatmapa nieczytelna na telefonach < 375px.
- **Proponowana zmiana:** Na mobile pokazac 3-4 miesiace naraz z mozliwoscia scrollowania.
- **Priorytet:** Low
- **Nadaje sie do ETAPU 2:** Tak

---

## Findings - Dostepnosc (A11y)

### A11Y-01: Brak semantycznych elementow HTML
- **Severity:** Medium
- **Lokalizacja:** Caly frontend
- **Problem:** Brak `<main>`, `<section>`, `<article>`, `<aside>`, `<nav>` (oprocz tab-nav w dashboard). Uzywane sa glownie `<div>` z klasami.
- **Wplyw:** Czytniki ekranowe nie moga okreslic struktury strony.
- **Rekomendacja:** Dodac landmarki ARIA lub semantyczne tagi HTML5.
- **Priorytet:** Medium

### A11Y-02: Brak `aria-label` na przyciskach z emoji
- **Severity:** Medium
- **Lokalizacja:** `templates/dashboard.html:401-406` (strzalki nawigacji heatmapy), przyciski kalendarza
- **Problem:** `<button onclick="prevMonth()">←</button>` - brak opisu dla czytnika.
- **Wplyw:** Czytnik ekranowy odczyta "button" bez kontekstu.
- **Rekomendacja:** Dodac `aria-label="Poprzedni miesiac"` itp.
- **Priorytet:** Medium

### A11Y-03: Contrast ratio na `--text-muted`
- **Severity:** Medium
- **Lokalizacja:** Wszystkie strony
- **Problem:** `--text-muted: #6b6b80` na tle `--bg-dark: #0a0a12` daje contrast ratio ~3.5:1. WCAG AA wymaga 4.5:1 dla tekstu normalnego.
- **Wplyw:** Tekst "muted" nieczytelny dla osob z oslabiona zdolnoscia widzenia.
- **Rekomendacja:** Podniesc kolor do ~`#8888a0` (ratio >= 4.5:1).
- **Priorytet:** Medium

### A11Y-04: Formularz logowania - brak `for` na labelach
- **Severity:** Low
- **Lokalizacja:** `templates/dashboard.html:513-519`
- **Problem:** `<label>Nazwa uzytkownika</label>` nie ma atrybutu `for` wiazacego z inputem.
- **Wplyw:** Klikniecie na label nie aktywuje inputa.
- **Rekomendacja:** Dodac `<label for="loginUsername">`.
- **Priorytet:** Low

### A11Y-05: Modaly nie lapią focus trap
- **Severity:** Low
- **Lokalizacja:** Modal workout, modal logowania
- **Problem:** Po otwarciu modalu focus nie jest przenoszony do modalu. Tab key moze nawigowac po elementach za modalem.
- **Wplyw:** Nawigacja klawiatura bledna w modalach.
- **Rekomendacja:** Dodac focus trap: przy otwarciu modalu ustawic focus na pierwszym elemencie, przy Tab na ostatnim - wracac do pierwszego.
- **Priorytet:** Low

### A11Y-06: Wykresy brak alternatywnego tekstu
- **Severity:** Low
- **Lokalizacja:** Wszystkie wykresy (daily chart, hourly chart, weekly chart, heatmap)
- **Problem:** Wykresy sa renderowane jako `<div>` z inline styles. Brak tekstowej alternatywy dla czytnikow ekranowych.
- **Wplyw:** Osoby korzystajace z czytnikow nie maja dostepu do danych statystycznych.
- **Rekomendacja:** Dodac `aria-label` z wartoscia liczbowa lub tabelke teksowa jako alternatywe.
- **Priorytet:** Low

### A11Y-07: Keyboard navigation - przyciski kalendarza
- **Severity:** Low
- **Lokalizacja:** Kalendarz w dashboard
- **Problem:** Dni kalendarza sa `<div>` z `onclick`. Nie sa dostepne przez klawiature (Tab + Enter).
- **Wplyw:** Uzytkownicy klawiatury nie moga dodac treningu.
- **Rekomendacja:** Uzyc `<button>` zamiast `<div>` lub dodac `tabindex="0"` + `role="button"` + keydown handler.
- **Priorytet:** Low

### A11Y-08: `user-scalable=no` na calendar.html
- **Severity:** Low
- **Lokalizacja:** `templates/calendar.html:6`, `templates/index.html:6`
- **Problem:** `<meta name="viewport" content="..., maximum-scale=1.0, user-scalable=no">` blokuje powiekszanie strony.
- **Wplyw:** Osoby slabowidzace nie moga powiekszyc tekstu.
- **Rekomendacja:** Usunac `maximum-scale=1.0, user-scalable=no`.
- **Priorytet:** Low
