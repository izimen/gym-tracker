# 🏋️ Gym Tracker

> Real-time gym occupancy tracking + workout calendar

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)
![Cloud Run](https://img.shields.io/badge/Google%20Cloud-Run-orange.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

A self-hosted gym tracker that scrapes occupancy data from eFitness-powered gym portals and provides a beautiful dashboard with workout tracking features.

## ✨ Features

### 📊 Gym Occupancy Monitoring
- **Live counter** - Current number of people at the gym, with live deviation indicator (`X% mniej/więcej` vs historical average)
- **Statistics** - Averages by day of week, hour, and trends
- **Best/Worst Hours** - Analysis of optimal training times

### 📅 Workout Calendar
- **Body part tracking** - Customize categories for your routine
- **Weight tracking** - Log weights, sets, and reps
- **Personal Records** - Automatic PR tracking
- **Yearly heatmap** - GitHub-style activity visualization

### 📈 Data Analytics
- **Data completeness indicators** - Visual dots showing data quality per day:
  - 🟢 Green: Full data collected
  - 🟡 Yellow border: Partial data (1-3 hours missing)
  - ⚪ Gray: Holiday/early closure detected
  - 🔴 Red: No data
- **Smart holiday detection** - Automatically detects early closures
- **Debug endpoint** - `/api/debug/day/YYYY-MM-DD` for data inspection

### 👥 Multi-User Support
- User authentication system
- Isolated workout data per user
- Admin panel

## 🚀 Quick Start

### Requirements
- Python 3.11+
- Google Cloud account with Firestore
- Access to an eFitness-powered gym portal

### Local Installation

```bash
# Clone the repo
git clone https://github.com/your-username/gym-tracker.git
cd gym-tracker

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your values (see Configuration below)

# Run
python app.py
```

Open http://localhost:5000

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GYM_URL` | Your gym's eFitness portal URL (e.g., `https://your-gym.cms.efitness.com.pl`) | ✅ |
| `GYM_EMAIL` | Login email for the gym portal | ✅ |
| `GYM_PASSWORD` | Login password for the gym portal | ✅ |
| `ADMIN_SECRET` | Secret token for admin endpoints | ✅ |
| `PORT` | Server port (default: 5000) | ❌ |

### Google Cloud Firestore
The application requires Firestore for data storage. Set `GOOGLE_APPLICATION_CREDENTIALS` or deploy to Cloud Run with an appropriate service account.

## 🔧 Customization

### Gym Operating Hours

Edit `database.py` and modify `GYM_HOURS` to match your gym's schedule:

```python
GYM_HOURS = {
    'weekday': (6, 23),  # Monday-Friday: 6:00 - 24:00 (last slot 23:00-00:00)
    'weekend': (8, 19),  # Saturday-Sunday: 8:00 - 20:00
}
```

### Workout Categories

Customize body parts in `database.py` by modifying `BODY_PARTS`:

```python
BODY_PARTS = {
    'chest': {'name': 'Chest', 'emoji': '💪', 'color': '#FF6B6B'},
    'back': {'name': 'Back', 'emoji': '🔙', 'color': '#4ECDC4'},
    # Add your own categories...
}
```

### Deployment Configuration

For forked repositories deploying to Google Cloud:

1. Add `GCP_PROJECT_ID` to your GitHub repository secrets
2. Add `GCP_SA_KEY` with your service account credentials
3. Push to `main` to trigger automatic deployment

## 🌐 Deployment (Google Cloud Run)

The repo includes automatic deployment via GitHub Actions:

1. Add secrets in GitHub repo settings:
   - `GCP_PROJECT_ID`: Your Google Cloud project ID
   - `GCP_SA_KEY`: Service account key JSON
2. Push to `main` branch to trigger deployment
3. Set environment variables in Cloud Run Console

## 📡 API Endpoints

### Public
| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard |
| `GET /calendar` | Workout calendar |
| `GET /api/occupancy` | Current occupancy |
| `GET /api/stats` | Historical statistics |
| `GET /health` | Health check |

### Workouts (require auth)
| Endpoint | Description |
|----------|-------------|
| `POST /api/workout` | Save workout |
| `GET /api/workouts/dashboard` | Dashboard stats |
| `GET /api/analytics/weekly` | Weekly statistics |
| `GET /api/analytics/heatmap/{year}` | Yearly heatmap |
| `GET /api/analytics/completeness/{year}/{month}` | Data completeness per day |
| `GET /api/debug/day/{date}` | Debug raw hourly data |

### Admin (require `?secret=ADMIN_SECRET`)
| Endpoint | Description |
|----------|-------------|
| `GET /api/admin/users` | List users |
| `POST /api/admin/reset-password` | Reset password |

## 🛡️ Security

- Credentials stored exclusively in environment variables
- Rate limiting on auth endpoints
- Admin endpoints protected by secret
- See [SECURITY.md](SECURITY.md) for vulnerability reporting

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Add docstrings to new functions
- Update documentation for new features
- Test locally before submitting PRs

## 📁 Project Structure

```
gym-tracker/
├── app.py                       # Flask app: pages, scraper, security headers, CSRF
├── extensions.py                # Shared: limiter, FIRESTORE_ENABLED, auth helpers
├── database.py                  # Firestore data layer, analytics, account lockout
├── routes/
│   ├── auth.py                  # register, login, logout, session
│   ├── admin.py                 # user mgmt, data reset, debug, export
│   ├── workouts.py              # CRUD, month, dashboard, strength, progression
│   └── analytics.py             # weekly, heatmap, comparison, best-hours
├── templates/
│   ├── base.html                # Shared head, fonts, CSS vars, DOMPurify
│   ├── dashboard.html           # Main dashboard (extends base)
│   ├── calendar.html            # Standalone calendar (extends base)
│   └── index.html               # Legacy page (extends base)
├── static/
│   ├── css/                     # dashboard.css, calendar.css, home.css
│   └── js/                      # dashboard.js, calendar.js, home.js
├── tests/                       # pytest unit tests (27 tests)
├── scripts/security/            # scan_secrets.sh, validate_env.sh, security_audit.sh
├── docs/
│   ├── audit/                   # 16 audit documents (360 security/architecture review)
│   └── FEATURE-IDEAS.md         # 13-feature roadmap
├── .github/workflows/
│   ├── deploy.yml               # Auto-deploy to Cloud Run
│   └── security-scan.yml        # Security scanning
├── Dockerfile
├── requirements.txt
├── CLAUDE.md                    # Project instructions for Claude Code
├── LICENSE
├── README.md
└── SECURITY.md
```

## 📱 PWA

Add to your phone's home screen:
- **Android**: Chrome → Menu → "Add to Home Screen"
- **iPhone**: Safari → Share → "Add to Home Screen"

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

Made with 💪 for gym enthusiasts everywhere

