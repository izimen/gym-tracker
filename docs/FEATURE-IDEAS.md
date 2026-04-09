# Pomysly na nowe statystyki i funkcje — Gym Tracker

Research z 4 rownoczesnych agentow (kwiecien 2026).
Fokus: praktyczne, oparte na danych, mozliwe do zbudowania z istniejacych danych Firestore.

---

## A. OBLOZENOSC SILOWNI — nowe insighty

### A1. Prognoza "Kiedy najlepiej isc?" (WYSOKI PRIORYTET)
Lista godzin od teraz do zamkniecia, posortowana od najmniej zatloczonych.
Dane: srednia z ostatnich 4 tygodni dla TEGO dnia tygodnia per godzina.
Juz istnieje `get_weekday_hour_average()` — wystarczy wywolac w petli i posortowac.

### A2. Odchylenie od normy — "Dzis jest spokojniej niz zwykle"
Porownanie aktualnej frekwencji ze srednia dla tego dnia+godziny.
Np.: "Teraz: 45 osob (zwykle ~62 o tej porze — 27% mniej)".
Dane: `get_weekday_hour_average()` vs biezacy scraping. Prosty ale bardzo przydatny.

### A3. Trend frekwencji — "Silownia robi sie tloczniejsza?"
Srednia max frekwencja z ostatnich 4 tyg vs poprzednich 4 tyg.
Prosta zmiana procentowa + strzalka. Mozna rozbic na weekday vs weekend.
Dane juz w `_preprocess_daily_hourly()`.

### A4. Heatmapa godzina x dzien (macierz 7x18)
Macierz 7 dni x 18 godzin z kolorami zielony->czerwony.
Jednym rzutem oka widac "ciche okna". Lepsza wizualizacja niz obecna lista top-3.

### A5. Stabilnosc godziny — "Czy 7:00 jest ZAWSZE spokojne?"
Oproc sredniej — odchylenie standardowe per godzina.
Niska srednia + niskie std = bezpieczny wybor. Niska + wysokie std = loteria.

### A6. Czas do szczytu — "Ile mam czasu?"
Na podstawie krzywej dla dzisiejszego dnia: "Szczyt za 2h (ok. 17:00)" lub "Szczyt byl, teraz maleje".

### A7. Twoje godziny vs tlum
Porownanie frekwencji w godzinach TWOICH treningow vs ogolna srednia.
"Gdybys przesunol trening o godzine wczesniej, ominalbys 30% ludzi."

---

## B. TRENING — nowe analityki

### B1. Streak Tracker (WYSOKI PRIORYTET)
Aktualny streak, najdluzszy streak, "streak at risk".
Streak = tygodnie z min. X treningami (nie dni z rzedu — bardziej realistyczne).
Obliczanie z samych dat treningow. Silny motywator wg badan.

### B2. Balans grup miesniowych — wykres radarowy (WYSOKI PRIORYTET)
Proporcje czestotliwosci 8 partii w ostatnich 30/60/90 dniach.
Juz istnieje `get_body_part_counts` — rozszerzenie. Natychmiast widac dysproporcje.

### B3. Volume treningowy w czasie (tygodniowy trend)
kg x serie x powtorzenia per tydzien, wykres 12 tygodni.
Uzupelnia istniejacy monthly_volume o trend — widac czy rosnie czy stagnuje.

### B4. Czas regeneracji per partia
Dla kazdej partii: ile dni temu trenowana, sredni odstep z historii.
Kolorystyka: zielony (gotowe 48h+), zolty (mozna), czerwony (za wczesnie <48h).
Praktyczna pomoc w planowaniu nastepnego treningu.

### B5. Estymowany 1RM (One Rep Max)
Automatyczne obliczenie z zestawow (formula Epley: weight x (1 + reps/30)).
Wykres 1RM w czasie — widac postep silowy bez testowania max.
Najczesciej chwalona funkcja w recenzjach Strong i Hevy.

### B6. Push/Pull/Legs proporcje
Auto-klasyfikacja: Klatka+Barki+Triceps=Push, Plecy+Biceps=Pull, Nogi+Posladki=Legs.
Stosunek procentowy w czasie. Wykrywa "za duzo push, za malo pull".

### B7. Rozklad treningow w tygodniu
Histogram: ile treningow w kazdy dzien tygodnia z calej historii.
Pokazuje wzorce — pomaga planowac i rownowazyc tydzien.

### B8. Czestotliwosc tygodniowa z celem
Srednia treningow/tydzien + cel (np. 4x/tyg) + procent realizacji.
Rozszerzenie istniejacego `get_weekly_workout_history`.

---

## C. MOTYWACJA I GAMIFIKACJA

### C1. Kamienie milowe (milestones)
Auto-odznaczenia: 10/25/50/100 treningow, pierwszy miesiac non-stop, nowy PR.
"Jeszcze 3 treningi do 50!" — goal gradient effect.

### C2. Tygodniowy cel z paskiem postepu (WYSOKI PRIORYTET)
Target "3 treningi w tym tygodniu" + progress bar.
Badania: konkretne krotkoterminowe cele zwieksza adherencje o 20-30%.

### C3. Podsumowanie tygodnia
Auto-summary w niedziele: ile treningow, volume, porownanie z poprzednim tyg.
3-4 linijki. Wzmacnia nawyk przez refleksje.

### C4. Wykrywanie plateau
Automatyczne wykrywanie stagnacji ciezaru/volume per partia.
Sugestia: "Bench press bez zmiany od 3 tygodni — czas na deload?"
Najczesciej wymieniane jako brakujace w recenzjach fitness appek.

---

## D. INSPIRACJA Z NAJLEPSZYCH APPEK

| Funkcja | Apka | Status w naszym projekcie |
|---------|------|--------------------------|
| Estymowany 1RM | Strong, Hevy | Brak — latwe do dodania |
| Volume per grupa | JEFIT, Hevy | Czesciowy (monthly_volume) |
| Mapa ciala z intensywnoscia | Hevy, JEFIT | Brak — radar chart jako alternatywa |
| Auto-wykrywanie PR | Strong | Czesciowy (max kg, brak auto-notyfikacji) |
| Porownanie okres vs okres | Hevy, FitNotes | Czesciowy (miesieczne) |
| Streak tracking | FitNotes, Strong | Brak |
| Prognoza oblozenosci | Google Fit, PerfectGym | Brak — dane sa, brak UI |
| Czas odpoczynku/treningu | Hevy | Brak (brakuje godziny treningu) |

---

## PRIORYTET IMPLEMENTACJI

### Faza 1 — szybkie wygrane (dane juz sa, min. naklad):
1. **A1** — Prognoza "kiedy isc" (sortowana lista godzin)
2. **A2** — Odchylenie od normy ("spokojniej niz zwykle")
3. **B1** — Streak tracker
4. **C2** — Tygodniowy cel + progress bar
5. **B4** — Czas regeneracji per partia

### Faza 2 — sredni naklad:
6. **B2** — Radar balans grup miesniowych
7. **B5** — Estymowany 1RM
8. **A4** — Heatmapa godzina x dzien
9. **B3** — Volume trend tygodniowy

### Faza 3 — wiekszy naklad:
10. **B6** — Push/Pull/Legs proporcje
11. **C4** — Wykrywanie plateau
12. **A7** — Twoje godziny vs tlum
13. **A5** — Stabilnosc godziny (std dev)
