# 🏋️ CubeFitness Gym Tracker

> Śledzenie obłożenia siłowni w czasie rzeczywistym + kalendarz treningów

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)
![Cloud Run](https://img.shields.io/badge/Google%20Cloud-Run-orange.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

## ✨ Funkcje

### 📊 Monitoring Siłowni
- **Live counter** - aktualna liczba osób na siłowni
- **Statystyki** - średnie dla dni tygodnia, godzin, trendów
- **Best/Worst Hours** - analiza najlepszych godzin do treningu
- **New Year Effect** - porównanie styczeń vs grudzień

### 📅 Kalendarz Treningów
- **Śledzenie partii ciała** - ramiona, plecy, nogi, klatka itd.
- **Weight tracking** - zapisywanie ciężarów, serii, powtórzeń
- **Personal Records** - automatyczne śledzenie PR-ów
- **Heatmapa roczna** - wizualizacja aktywności

### 👥 Wieloużytkownikowy
- System logowania
- Izolowane dane dla każdego użytkownika
- Panel administracyjny

## 🚀 Quick Start

### Wymagania
- Python 3.11+
- Konto GCP z Firestore

### Instalacja lokalna

```bash
# Sklonuj repo
git clone https://github.com/izimen/gym-tracker.git
cd gym-tracker

# Stwórz virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# lub: source venv/bin/activate  # Linux/Mac

# Zainstaluj zależności
pip install -r requirements.txt

# Skonfiguruj zmienne środowiskowe
cp .env.example .env
# Edytuj .env i dodaj swoje dane

# Uruchom
python app.py
```

Otwórz http://localhost:5000

## ⚙️ Konfiguracja

### Zmienne środowiskowe

| Zmienna | Opis | Wymagane |
|---------|------|----------|
| `GYM_EMAIL` | Email do konta CubeFitness | ✅ |
| `GYM_PASSWORD` | Hasło do konta CubeFitness | ✅ |
| `ADMIN_SECRET` | Secret dla endpointów admin | ✅ |
| `PORT` | Port serwera (default: 5000) | ❌ |

### Google Cloud Firestore
Aplikacja wymaga Firestore do przechowywania danych. Ustaw `GOOGLE_APPLICATION_CREDENTIALS` lub deploy na Cloud Run z odpowiednim service account.

## 🌐 Deployment (Google Cloud Run)

Repo zawiera automatyczny deployment przez GitHub Actions:

1. Dodaj secret `GCP_SA_KEY` w GitHub repo settings
2. Push do `main` uruchomi deployment
3. Ustaw zmienne środowiskowe w Cloud Run Console

## 📡 API Endpoints

### Publiczne
| Endpoint | Opis |
|----------|------|
| `GET /` | Dashboard |
| `GET /calendar` | Kalendarz treningów |
| `GET /api/occupancy` | Aktualne obłożenie |
| `GET /api/stats` | Statystyki historyczne |
| `GET /health` | Health check |

### Treningi (wymagają auth)
| Endpoint | Opis |
|----------|------|
| `POST /api/workout` | Zapisz trening |
| `GET /api/workouts/dashboard` | Dashboard stats |
| `GET /api/analytics/weekly` | Tygodniowe statystyki |
| `GET /api/analytics/heatmap/{year}` | Heatmapa roczna |

### Admin (wymagają `?secret=ADMIN_SECRET`)
| Endpoint | Opis |
|----------|------|
| `GET /api/admin/users` | Lista użytkowników |
| `POST /api/admin/reset-password` | Reset hasła |

## 🛡️ Security

- Credentials przechowywane wyłącznie w env vars
- Rate limiting na endpointach auth
- Admin endpoints chronione secretem
- Zobacz [SECURITY.md](SECURITY.md) dla polityki zgłaszania luk

## 📁 Struktura projektu

```
gym-tracker/
├── app.py              # Flask application
├── database.py         # Firestore operations
├── templates/
│   ├── dashboard.html  # Główny dashboard
│   ├── calendar.html   # Kalendarz treningów
│   └── index.html      # Legacy view
├── .github/workflows/
│   ├── deploy.yml      # Auto-deploy to Cloud Run
│   └── security-scan.yml # Security scanning
├── Dockerfile
├── requirements.txt
└── SECURITY.md
```

## 📱 PWA

Dodaj do ekranu głównego telefonu:
- **Android**: Chrome → Menu → "Dodaj do ekranu głównego"
- **iPhone**: Safari → Share → "Dodaj do ekranu początkowego"

## 📄 License

MIT License - zobacz [LICENSE](LICENSE)

---

Stworzono z 💪 dla CubeFitness
