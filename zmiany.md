# Dziennik Zmian (Changelog) - 2026-01-10

## 🔒 Bezpieczeństwo i Backend (`app.py`, `security headers`)

### 1. Eliminacja podatności IDOR (Insecure Direct Object References)
- **Problem:** Aplikacja polegała na `user_id` przesyłanym w ciele żądania, co pozwalało na manipulację danymi innych użytkowników.
- **Rozwiązanie:** Wdrożono funkcję `get_current_user_id()`, która bezpiecznie pobiera ID zalogowanego użytkownika z sesji serwera (Flask Session). Endpointy takie jak zapisu treningu (`/api/workout`) używają teraz wyłącznie tego zweryfikowanego ID.

### 2. Utwardzenie Sesji (Session Hardening)
- Skonfigurowano flagi ciasteczek sesyjnych dla zwiększenia bezpieczeństwa:
  - `SESSION_COOKIE_HTTPONLY=True`: Chroni przed kradzieżą sesji przez ataki XSS.
  - `SESSION_COOKIE_SAMESITE='Lax'`: Chroni przed atakami CSRF.
  - `SESSION_COOKIE_SECURE=True`: Wymusza przesyłanie ciasteczek tylko po HTTPS (aktywne w środowisku produkcyjnym).

### 3. Nagłówki Bezpieczeństwa (Security Headers)
Zaimplementowano zestaw nowoczesnych nagłówków HTTP:
- `Permissions-Policy`: Blokada dostępu do wrażliwych API przeglądarki (kamera, mikrofon, lokalizacja).
- `Cross-Origin-Opener-Policy (COOP)`: `same-origin`.
- `Cross-Origin-Embedder-Policy (COEP)`: `require-corp`.
- `Cross-Origin-Resource-Policy (CORP)`: `same-origin`.

### 4. Konfiguracja CORS
- Zmodyfikowano konfigurację CORS, aby w środowisku produkcyjnym nie dopuszczać pochodzenia `localhost`, co zwiększa bezpieczeństwo wdrożenia.

---

## 🎨 Frontend - Refaktoryzacja pod Strict CSP (W toku)

Celem jest uzyskanie oceny **A+** na Mozilla Observatory poprzez całkowite usunięcie `unsafe-inline` z polityki Content Security Policy.

### 1. `index.html` (Strona Główna)
- **CSS:** Wyniesiono wszystkie style inline do nowego pliku `static/css/home.css`.
- **JavaScript:** Wyniesiono logikę do nowego pliku `static/js/home.js`.
- **Interakcje:** Zastąpiono atrybut `onclick` na przycisku odświeżania nasłuchem zdarzeń (`addEventListener`).
- **Efekt:** Plik HTML jest czysty, bez bloków `<style>` i `<script>`.

### 2. `dashboard.html` (Panel Użytkownika)
- **CSS:** Style krytyczne (wcześniej inline) zostały przeniesione do `static/css/dashboard.css`.
- **JavaScript:** Cała logika została przeniesiona do `static/js/dashboard.js`.
- **Event Listeners:** 
  - Usunięto atrybuty `onclick` z elementów HTML (przyciski logowania, nawigacja kalendarza, modal).
  - Dodano odpowiednie identyfikatory (`id`) w HTML.
  - Zaimplementowano obsługę zdarzeń w `dashboard.js` wewnątrz bloku `DOMContentLoaded`.

---

## 📅 Kolejne kroki (Do realizacji teraz)

1. **Refaktoryzacja `calendar.html`:**
   - Wyniesienie stylów do `static/css/calendar.css`.
   - Wyniesienie skryptów do `static/js/calendar.js`.
   - Zamiana `onclick` na `addEventListener` (Strict CSP).
2. **Aktualizacja `app.py` (CSP):**
   - Finalne usunięcie `'unsafe-inline'` z nagłówka `Content-Security-Policy`.
   - Dodanie dyrektyw `base-uri 'self'`, `object-src 'none'`, `form-action 'self'`.
3. **Weryfikacja:** Sprawdzenie działania aplikacji i poprawności nagłówków.
