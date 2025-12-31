# CubeFitness Gym Occupancy Tracker 🏋️

Aplikacja do śledzenia liczby osób na siłowni CubeFitness Garwolin w czasie rzeczywistym.

## Funkcje

- 📊 Wyświetla aktualną liczbę osób na siłowni
- 🔄 Automatyczne odświeżanie co minutę
- 📱 Responsywny interfejs - działa świetnie na telefonie
- 🌙 Ciemny motyw przyjazny dla oczu
- ⚡ Szybki i lekki

## Jak uruchomić lokalnie

1. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

2. Uruchom aplikację:
```bash
python app.py
```

3. Otwórz przeglądarkę: http://localhost:5000

## Wdrożenie na Oracle Cloud (Free Tier)

### Krok 1: Utwórz konto Oracle Cloud
1. Wejdź na https://www.oracle.com/cloud/free/
2. Kliknij "Start for free"
3. Wypełnij formularz rejestracji
4. Potwierdź email i skonfiguruj konto

### Krok 2: Utwórz maszynę wirtualną (VM)
1. Zaloguj się do Oracle Cloud Console
2. Kliknij ☰ (menu) → Compute → Instances
3. Kliknij "Create Instance"
4. Nazwa: `gym-tracker`
5. **Image**: Ubuntu 22.04 (Always Free eligible)
6. **Shape**: VM.Standard.E2.1.Micro (Always Free - 1 OCPU, 1 GB RAM)
7. **Networking**: Utwórz nową VCN lub użyj istniejącej
8. **Add SSH keys**: Wygeneruj nowy klucz lub dodaj swój (zapisz klucz prywatny!)
9. Kliknij "Create"

### Krok 3: Skonfiguruj reguły firewall
1. Wejdź w szczegóły instancji
2. Kliknij "Virtual Cloud Network" → "Security Lists" → "Default Security List"
3. Kliknij "Add Ingress Rules"
4. Dodaj regułę:
   - Source CIDR: `0.0.0.0/0`
   - Destination Port Range: `5000`
   - Description: `Gym Tracker App`

### Krok 4: Połącz się z serwerem
```bash
ssh -i /ścieżka/do/klucza/prywatnego ubuntu@TWÓJ_PUBLICZNY_IP
```

### Krok 5: Zainstaluj wymagane oprogramowanie
```bash
# Aktualizuj system
sudo apt update && sudo apt upgrade -y

# Zainstaluj Python, pip i narzędzie unzip
sudo apt install python3 python3-pip python3-venv unzip -y
```

### Krok 6: Wyślij i rozpakuj aplikację
Możesz użyć programu (np. FileZilla, WinSCP) aby wysłać plik `gym-tracker.zip` na serwer do katalogu domowego (`/home/ubuntu`).

Następnie na serwerze:
```bash
# Rozpakuj paczkę
unzip gym-tracker.zip
cd gym-tracker

# WAŻNE: Napraw formatowanie pliku (Windows -> Linux)
sed -i 's/\r$//' setup_server.sh

# Uruchom instalator
bash setup_server.sh
```

### Krok 8: Skonfiguruj automatyczny restart
Utwórz usługę systemd:

```bash
sudo nano /etc/systemd/system/gym-tracker.service
```

Wklej:
```ini
[Unit]
Description=Gym Tracker App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/gym-tracker
Environment="PATH=/home/ubuntu/gym-tracker/venv/bin"
ExecStart=/home/ubuntu/gym-tracker/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Aktywuj usługę:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gym-tracker
sudo systemctl start gym-tracker
```

### Krok 9: Gotowe! 🎉
Otwórz w przeglądarce:
```
http://TWÓJ_PUBLICZNY_IP:5000
```

## Dodaj do ekranu głównego (telefon)

### Android (Chrome):
1. Otwórz stronę w Chrome
2. Kliknij ⋮ (menu)
3. Wybierz "Dodaj do ekranu głównego"

### iPhone (Safari):
1. Otwórz stronę w Safari
2. Kliknij 📤 (udostępnij)
3. Wybierz "Dodaj do ekranu początkowego"

## Zmiana danych logowania

Możesz ustawić dane logowania przez zmienne środowiskowe:

```bash
export GYM_EMAIL="twój@email.com"
export GYM_PASSWORD="twojehasło"
```

Lub edytuj bezpośrednio w `app.py`.

## Rozwiązywanie problemów

### Aplikacja nie działa
```bash
sudo systemctl status gym-tracker
sudo journalctl -u gym-tracker -f
```

### Nie mogę się połączyć
- Sprawdź czy port 5000 jest otwarty w Security Lists
- Sprawdź czy firewall na VM jest wyłączony: `sudo ufw status`
- Sprawdź czy aplikacja działa: `curl localhost:5000`

## API

- `GET /` - Główna strona
- `GET /api/occupancy` - Aktualne dane o obłożeniu (JSON)
- `GET /api/refresh` - Wymuś odświeżenie danych
- `GET /health` - Status aplikacji

---

Stworzono z ❤️ dla fanów CubeFitness Garwolin
