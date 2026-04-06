"""
CubeFitness Gym Entries Tracker
Backend server that scrapes gym entry data and serves it via API
"""

from flask import Flask, jsonify, render_template, request, redirect, session
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os
import secrets
from datetime import datetime, timedelta
import threading
import time
import pytz
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Import database module (Firestore)
try:
    import database
    FIRESTORE_ENABLED = True
    # Create admin user if not exists (preserves existing workout data)
    database.ensure_admin_user()
except Exception as e:
    logger.warning("Firestore not available: %s", e)
    FIRESTORE_ENABLED = False

app = Flask(__name__)

# Session secret key — MUST be set via env var in production
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    _secret_file = os.path.join(os.environ.get('APP_HOME', '/tmp'), '.flask_secret')
    try:
        with open(_secret_file, 'r') as f:
            _secret_key = f.read().strip()
    except FileNotFoundError:
        _secret_key = secrets.token_hex(32)
        try:
            with open(_secret_file, 'w') as f:
                f.write(_secret_key)
        except OSError:
            pass
    logger.warning("SECRET_KEY env var not set. Using file-based fallback.")
    logger.warning("Set SECRET_KEY env var in Cloud Run for stable sessions across deployments.")
app.secret_key = _secret_key

# Session cookie configuration
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=90)

# CORS Configuration
allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
CORS(app, origins=[o.strip() for o in allowed_origins], supports_credentials=True)

# Initialize shared extensions
import extensions
extensions.FIRESTORE_ENABLED = FIRESTORE_ENABLED
extensions.ADMIN_SECRET = os.environ.get('ADMIN_SECRET')
extensions.limiter.init_app(app)

# Enable GZIP compression
from flask_compress import Compress
Compress(app)

# Register Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.workouts import workouts_bp
from routes.analytics import analytics_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(workouts_bp)
app.register_blueprint(analytics_bp)

limiter = extensions.limiter


# =============================================================================
# SCRAPER CONFIGURATION
# =============================================================================

GYM_EMAIL = os.environ.get('GYM_EMAIL')
GYM_PASSWORD = os.environ.get('GYM_PASSWORD')
GYM_URL = os.environ.get('GYM_URL')
LOGIN_URL = f'{GYM_URL}/Login/SystemLogin' if GYM_URL else None
DATA_URL = f'{GYM_URL}/na-terenie-klubu' if GYM_URL else None

if not GYM_URL:
    logger.warning("GYM_URL environment variable is not set!")
    logger.warning("Set it to your gym's eFitness CMS portal URL (e.g., https://your-gym.cms.efitness.com.pl)")
if not GYM_EMAIL or not GYM_PASSWORD:
    logger.warning("GYM_EMAIL and GYM_PASSWORD environment variables are not set!")
    logger.warning("The application will not be able to fetch gym data.")

REQUEST_TIMEOUT = 15
REFRESH_COOLDOWN = 30
last_refresh_time = 0
refresh_lock = threading.Lock()

# Cache for entries data — uses atomic dict replacement for thread safety
entries_cache = {
    'entries_today': 0,
    'last_updated': None,
    'status': 'initializing',
    'error': None
}

# Global session variable
current_session = None
session_lock = threading.Lock()


def get_gym_session(force_new=False):
    """Get an active session, creating a new one if necessary"""
    global current_session

    with session_lock:
        if current_session and not force_new:
            return current_session

        logger.info("Creating new login session...")
        gym_sess = requests.Session()
        gym_sess.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        })

        try:
            gym_sess.get(GYM_URL, timeout=REQUEST_TIMEOUT)
            login_data = {'Login': GYM_EMAIL, 'Password': GYM_PASSWORD, 'RememberMe': 'false'}
            login_response = gym_sess.post(LOGIN_URL, data=login_data, allow_redirects=True, timeout=REQUEST_TIMEOUT)

            if login_response.status_code == 200:
                logger.info("Login successful")
                current_session = gym_sess
                return gym_sess
            else:
                logger.warning("Login failed with status: %s", login_response.status_code)
                return None
        except requests.Timeout:
            logger.warning("Login timeout")
            return None
        except Exception as e:
            logger.error("Login error: %s", e)
            return None


def save_to_firestore(entries_count: int):
    """Helper function to save entries to Firestore (daily + hourly)"""
    if FIRESTORE_ENABLED:
        try:
            database.save_daily_entry(entries_count)
            database.save_hourly_occupancy(entries_count)
        except Exception as e:
            logger.error("Firestore save error: %s", e)


def fetch_entries_data():
    """Fetch current gym entries count. Uses atomic dict replacement for thread safety."""
    global entries_cache

    if not GYM_URL or not DATA_URL:
        entries_cache = {'entries_today': 0, 'last_updated': None, 'status': 'error', 'error': 'GYM_URL not configured'}
        return

    try:
        gym_sess = get_gym_session()
        if not gym_sess:
            entries_cache = {'entries_today': 0, 'last_updated': None, 'status': 'error', 'error': 'Nie udało się zalogować'}
            return

        response = gym_sess.get(DATA_URL, timeout=REQUEST_TIMEOUT)

        if response.url.startswith(LOGIN_URL) or '/Login' in response.url:
            logger.info("Session expired, logging in again...")
            gym_sess = get_gym_session(force_new=True)
            if gym_sess:
                response = gym_sess.get(DATA_URL, timeout=REQUEST_TIMEOUT)
            else:
                entries_cache = {'entries_today': 0, 'last_updated': None, 'status': 'error', 'error': 'Sesja wygasła, ponowne logowanie nieudane'}
                return

        if response.status_code != 200:
            entries_cache = {'entries_today': 0, 'last_updated': None, 'status': 'error', 'error': f'Błąd HTTP: {response.status_code}'}
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        match = re.search(r'Aktualnie\s+w\s+klubie\s*(\d+)\s*/\s*\d+', page_text, re.IGNORECASE)
        entries_today = None

        if match:
            entries_today = int(match.group(1))
        else:
            numbers = re.findall(r'(\d+)\s*/\s*(\d+)', page_text)
            for entries, max_c in numbers:
                if int(max_c) > 50:
                    entries_today = int(entries)
                    break

        if entries_today is not None:
            tz = pytz.timezone('Europe/Warsaw')
            updated_at = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
            entries_cache = {
                'entries_today': entries_today,
                'last_updated': updated_at,
                'status': 'ok',
                'error': None
            }
            logger.info("Entries today: %d (updated %s)", entries_today, updated_at)
            save_to_firestore(entries_today)
        else:
            logger.warning("Could not find entry numbers. Page text sample: %s", page_text[:100])
            entries_cache = {'entries_today': 0, 'last_updated': None, 'status': 'error', 'error': 'Nie znaleziono danych o wejściach'}

    except requests.Timeout:
        entries_cache = {'entries_today': 0, 'last_updated': None, 'status': 'error', 'error': 'Przekroczono limit czasu połączenia'}
        logger.warning("Request timeout")
    except Exception as e:
        entries_cache = {'entries_today': 0, 'last_updated': None, 'status': 'error', 'error': str(e)}
        logger.error("Error fetching data: %s", e)


def background_updater():
    """Background thread that updates entries data periodically"""
    while True:
        fetch_entries_data()
        time.sleep(180)


# Start background updater
updater_thread = threading.Thread(target=background_updater, daemon=True)
updater_thread.start()


# =============================================================================
# CORE PAGE & DATA ROUTES
# =============================================================================

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('dashboard.html')


@app.route('/legacy')
def legacy():
    """Old main page (backup)"""
    return render_template('index.html')


@app.route('/api/occupancy')
@limiter.limit("200 per hour")
def get_occupancy():
    """API endpoint to get current entries (legacy endpoint name)"""
    cache = entries_cache
    if cache.get('status') == 'initializing' or cache.get('last_updated') is None:
        fetch_entries_data()
        cache = entries_cache
    return jsonify(cache)


@app.route('/api/entries')
@limiter.limit("200 per hour")
def get_entries():
    """API endpoint to get current entries"""
    return jsonify(entries_cache)


@app.route('/api/stats')
@limiter.limit("100 per hour")
def get_stats():
    """API endpoint to get historical statistics"""
    cache = entries_cache
    result = {
        'entries_today': cache.get('entries_today', 0),
        'week_ago': None,
        'week_ago_date': None,
        'average_for_weekday': None,
        'weekday_name': None,
        'history_count': 0,
        'firestore_enabled': FIRESTORE_ENABLED
    }

    if FIRESTORE_ENABLED:
        try:
            week_ago_data = database.get_week_ago_entries()
            if week_ago_data:
                result['week_ago'] = week_ago_data['entries']
                result['week_ago_date'] = week_ago_data['date']
            result['average_for_weekday'] = database.get_average_for_weekday()
            result['weekday_name'] = database.get_current_weekday_name()
            result['history_count'] = database.get_history_count()
        except Exception as e:
            logger.error("Stats fetch error: %s", e)
            result['error'] = 'Failed to load stats'

    return jsonify(result)


@app.route('/api/refresh')
def refresh_data():
    """Force refresh entries data with rate limiting"""
    global last_refresh_time

    with refresh_lock:
        current_time = time.time()
        time_since_last = current_time - last_refresh_time

        if time_since_last < REFRESH_COOLDOWN:
            remaining = int(REFRESH_COOLDOWN - time_since_last)
            cache = entries_cache
            return jsonify({
                **cache,
                'rate_limited': True,
                'retry_after': remaining
            }), 429

        last_refresh_time = current_time

    fetch_entries_data()
    return jsonify(entries_cache)


@app.route('/health')
def health():
    """Health check endpoint with Firestore connectivity test"""
    result = {'status': 'healthy', 'timestamp': datetime.now().isoformat(), 'firestore': False}
    if FIRESTORE_ENABLED:
        try:
            db = database.get_db()
            db.collection('daily_entries').limit(1).get()
            result['firestore'] = True
        except Exception as e:
            result['status'] = 'degraded'
            result['firestore_error'] = str(e)
    return jsonify(result)


# =============================================================================
# SECURITY HEADERS & CACHING
# =============================================================================

@app.before_request
def enforce_https():
    """Redirect HTTP to HTTPS in production (Cloud Run sets X-Forwarded-Proto)"""
    if request.headers.get('X-Forwarded-Proto') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)


@app.before_request
def csrf_check():
    """CSRF protection: require X-Requested-With header on state-changing requests (SEC-07).
    Browsers won't send custom headers cross-origin without CORS preflight."""
    if request.method in ('POST', 'PUT', 'DELETE') and request.path.startswith('/api/'):
        if not request.headers.get('X-Requested-With'):
            return jsonify({'error': 'Missing X-Requested-With header'}), 403


@app.after_request
def add_security_headers(response):
    """Add security, CSP, and caching headers to all responses (unified)"""

    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '0'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'

    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https://fav.farm; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp

    if request.path.startswith('/static/') and request.path.endswith('.min.js'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=3600'
    elif request.path.endswith('.html') or request.path == '/':
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'

    return response


if __name__ == '__main__':
    logger.info("Starting CubeFitness Entries Tracker...")
    fetch_entries_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
