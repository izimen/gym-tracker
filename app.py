"""
CubeFitness Gym Entries Tracker
Backend server that scrapes gym entry data and serves it via API
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime
import threading
import time
import pytz

# Import database module (Firestore)
try:
    import database
    FIRESTORE_ENABLED = True
    # Create admin user if not exists (preserves existing workout data)
    database.ensure_admin_user()
except Exception as e:
    print(f"Firestore not available: {e}")
    FIRESTORE_ENABLED = False

app = Flask(__name__)
CORS(app)

# Configuration - MUST be set via environment variables
GYM_EMAIL = os.environ.get('GYM_EMAIL')
GYM_PASSWORD = os.environ.get('GYM_PASSWORD')
ADMIN_SECRET = os.environ.get('ADMIN_SECRET')
GYM_URL = 'https://cubefitness-garwolin.cms.efitness.com.pl'
LOGIN_URL = f'{GYM_URL}/Login/SystemLogin'
DATA_URL = f'{GYM_URL}/na-terenie-klubu'

# Validate required environment variables at startup
if not GYM_EMAIL or not GYM_PASSWORD:
    print("WARNING: GYM_EMAIL and GYM_PASSWORD environment variables are not set!")
    print("The application will not be able to fetch gym data.")

# Request timeout in seconds
REQUEST_TIMEOUT = 15

# Rate limiting for refresh endpoint (in seconds)
REFRESH_COOLDOWN = 30
last_refresh_time = 0
refresh_lock = threading.Lock()

# Cache for entries data
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
            
        print("Creating new login session...")
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        })
        
        try:
            # First, get the login page to obtain any CSRF tokens
            session.get(GYM_URL, timeout=REQUEST_TIMEOUT)
            
            # Login
            login_data = {
                'Login': GYM_EMAIL,
                'Password': GYM_PASSWORD,
                'RememberMe': 'false'
            }
            
            login_response = session.post(LOGIN_URL, data=login_data, allow_redirects=True, timeout=REQUEST_TIMEOUT)
            
            if login_response.status_code == 200:
                print("Login successful")
                current_session = session
                return session
            else:
                print(f"Login failed with status: {login_response.status_code}")
                return None
        except requests.Timeout:
            print("Login timeout")
            return None
        except Exception as e:
            print(f"Login error: {e}")
            return None


def save_to_firestore(entries_count: int):
    """Helper function to save entries to Firestore (daily + hourly)"""
    if FIRESTORE_ENABLED:
        try:
            # Save daily entry (existing)
            database.save_daily_entry(entries_count)
            # Save hourly occupancy (new - for best hours analysis)
            database.save_hourly_occupancy(entries_count)
        except Exception as e:
            print(f"Firestore save error: {e}")


def fetch_entries_data():
    """Fetch current gym entries count"""
    global entries_cache
    
    try:
        # Try to get data with current session
        session = get_gym_session()
        if not session:
            entries_cache['status'] = 'error'
            entries_cache['error'] = 'Nie udało się zalogować'
            return
        
        # Get the entries page
        response = session.get(DATA_URL, timeout=REQUEST_TIMEOUT)
        
        # Check if we were redirected to login page (session expired)
        if response.url.startswith(LOGIN_URL) or '/Login' in response.url:
            print("Session expired, logging in again...")
            session = get_gym_session(force_new=True)
            if session:
                response = session.get(DATA_URL, timeout=REQUEST_TIMEOUT)
            else:
                entries_cache['status'] = 'error'
                entries_cache['error'] = 'Sesja wygasła, ponowne logowanie nieudane'
                return

        if response.status_code != 200:
            entries_cache['status'] = 'error'
            entries_cache['error'] = f'Błąd HTTP: {response.status_code}'
            return
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Find "Aktualnie w klubie" and extract the first number (entries today)
        match = re.search(r'Aktualnie\s+w\s+klubie\s*(\d+)\s*/\s*\d+', page_text, re.IGNORECASE)
        
        entries_today = None
        
        if match:
            entries_today = int(match.group(1))
        else:
            # Try alternative patterns
            numbers = re.findall(r'(\d+)\s*/\s*(\d+)', page_text)
            for entries, max_c in numbers:
                if int(max_c) > 50:
                    entries_today = int(entries)
                    break
        
        if entries_today is not None:
            tz = pytz.timezone('Europe/Warsaw')
            entries_cache['entries_today'] = entries_today
            entries_cache['last_updated'] = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
            entries_cache['status'] = 'ok'
            entries_cache['error'] = None
            print(f"[{entries_cache['last_updated']}] Entries today: {entries_today}")
            
            # Save to Firestore
            save_to_firestore(entries_today)
        else:
            print("Could not find entry numbers. Page text sample: " + page_text[:100])
            entries_cache['status'] = 'error'
            entries_cache['error'] = 'Nie znaleziono danych o wejściach'
                
    except requests.Timeout:
        entries_cache['status'] = 'error'
        entries_cache['error'] = 'Przekroczono limit czasu połączenia'
        print("Request timeout")
    except Exception as e:
        entries_cache['status'] = 'error'
        entries_cache['error'] = str(e)
        print(f"Error fetching data: {e}")


def background_updater():
    """Background thread that updates entries data periodically"""
    while True:
        fetch_entries_data()
        time.sleep(180)  # Update every 3 minutes


# Start background updater
updater_thread = threading.Thread(target=background_updater, daemon=True)
updater_thread.start()


@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('dashboard.html')


@app.route('/legacy')
def legacy():
    """Old main page (backup)"""
    return render_template('index.html')


@app.route('/api/occupancy')
def get_occupancy():
    """API endpoint to get current entries (legacy endpoint name)"""
    # If cache is initializing or has no data, fetch fresh data now
    if entries_cache.get('status') == 'initializing' or entries_cache.get('last_updated') is None:
        fetch_entries_data()
    return jsonify(entries_cache)


@app.route('/api/entries')
def get_entries():
    """API endpoint to get current entries"""
    return jsonify(entries_cache)


@app.route('/api/stats')
def get_stats():
    """API endpoint to get historical statistics"""
    result = {
        'entries_today': entries_cache.get('entries_today', 0),
        'week_ago': None,
        'week_ago_date': None,
        'average_for_weekday': None,
        'weekday_name': None,
        'history_count': 0,
        'firestore_enabled': FIRESTORE_ENABLED
    }
    
    if FIRESTORE_ENABLED:
        try:
            # Get week ago data
            week_ago_data = database.get_week_ago_entries()
            if week_ago_data:
                result['week_ago'] = week_ago_data['entries']
                result['week_ago_date'] = week_ago_data['date']
            
            # Get average for this weekday
            result['average_for_weekday'] = database.get_average_for_weekday()
            result['weekday_name'] = database.get_current_weekday_name()
            
            # Get history count (cached to avoid expensive query)
            result['history_count'] = database.get_history_count()
        except Exception as e:
            print(f"Stats fetch error: {e}")
            result['error'] = str(e)
    
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
            return jsonify({
                **entries_cache,
                'rate_limited': True,
                'retry_after': remaining
            }), 429
        
        last_refresh_time = current_time
    
    fetch_entries_data()
    return jsonify(entries_cache)


# =============================================================================
# WORKOUT CALENDAR API ENDPOINTS
# =============================================================================

@app.route('/calendar')
def calendar():
    """Serve the calendar page"""
    return render_template('calendar.html')


@app.route('/api/workout', methods=['POST'])
def save_workout():
    """Save a workout for a date"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    data = request.get_json()
    
    if not data or 'date' not in data or 'body_parts' not in data:
        return jsonify({'error': 'Missing date or body_parts'}), 400
    
    date_str = data['date']
    body_parts = data['body_parts']
    weight_data = data.get('weight_data')
    notes = data.get('notes')
    user_id = data.get('user_id')  # User ID from frontend
    
    # Validate body parts
    valid_parts = database.BODY_PARTS.keys()
    for part in body_parts:
        if part not in valid_parts:
            return jsonify({'error': f'Invalid body part: {part}'}), 400
    
    try:
        database.save_workout(date_str, body_parts, weight_data, notes, user_id)
        return jsonify({'success': True, 'date': date_str})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workout/<date_str>', methods=['GET'])
def get_workout(date_str):
    """Get workout for a specific date"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        workout = database.get_workout(date_str, user_id)
        return jsonify(workout or {})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workout/<date_str>', methods=['DELETE'])
def delete_workout(date_str):
    """Delete workout for a specific date"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        database.delete_workout(date_str, user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workouts/month/<int:year>/<int:month>')
def get_month_workouts(year, month):
    """Get all workouts for a month"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        workouts = database.get_month_workouts(year, month, user_id)
        return jsonify({
            'year': year,
            'month': month,
            'workouts': workouts,
            'body_parts_config': database.BODY_PARTS
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workouts/dashboard')
def get_workout_dashboard():
    """Get all workout stats for the dashboard"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available', 'firestore_enabled': False}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        stats = database.get_workout_dashboard_stats(user_id)
        stats['firestore_enabled'] = True
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e), 'firestore_enabled': True}), 500


# =============================================================================
# ANALYTICS API ENDPOINTS
# =============================================================================

@app.route('/api/analytics/weekly')
def get_analytics_weekly():
    """Get weekly workout history for the last 12 weeks"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        data = database.get_weekly_workout_history(weeks=12, user_id=user_id)
        return jsonify({'weeks': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/heatmap/<int:year>')
def get_analytics_heatmap(year):
    """Get yearly heatmap data"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        data = database.get_yearly_heatmap_data(year, user_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/comparison')
def get_analytics_comparison():
    """Get month-to-month comparison"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        data = database.get_month_comparison(user_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/best-hours')
def get_analytics_best_hours():
    """Get best gym hours analysis"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    try:
        data = database.get_hourly_stats()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/extended')
def get_analytics_extended():
    """Get extended occupancy statistics for the dashboard"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    try:
        data = database.get_extended_occupancy_stats()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/new-year')
def get_new_year_stats():
    """Get New Year's resolution effect statistics - January vs December comparison"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    try:
        year = request.args.get('year', type=int)
        data = database.get_new_year_effect(year)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# AUTHENTICATION API ENDPOINTS
# =============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Register a new user"""
    if not FIRESTORE_ENABLED:
        return jsonify({'success': False, 'error': 'Firestore not available'}), 503
    
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    result = database.create_user(username, password)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """Login with username and password"""
    if not FIRESTORE_ENABLED:
        return jsonify({'success': False, 'error': 'Firestore not available'}), 503
    
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    result = database.authenticate_user(username, password)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 401


@app.route('/api/admin/reset-password', methods=['POST'])
def admin_reset_password():
    """Admin: Reset a user's password"""
    if not FIRESTORE_ENABLED:
        return jsonify({'success': False, 'error': 'Firestore not available'}), 503
    
    
    # Simple protection - require secret parameter
    secret = request.args.get('secret')
    if not ADMIN_SECRET or secret != ADMIN_SECRET:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    new_password = data.get('new_password', '')
    
    result = database.admin_reset_password(username, new_password)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400


@app.route('/api/admin/users')
def list_users():
    """Admin: List all users"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    
    # Simple protection
    secret = request.args.get('secret')
    if secret != 'cube2025reset':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        users = database.get_all_users()
        return jsonify({'users': users, 'count': len(users)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# ADMIN API ENDPOINTS
# =============================================================================

@app.route('/api/admin/reset-hourly')
def reset_hourly_data():
    """Reset hourly occupancy data - clears all records to start fresh"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    # Simple protection - require secret parameter
    secret = request.args.get('secret')
    if secret != 'cube2025reset':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        deleted_count = database.clear_hourly_occupancy()
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} hourly records',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/debug-weekday/<int:weekday>')
def debug_weekday_data(weekday):
    """Debug: Analyze data for a specific weekday (0=Mon, 4=Fri, 6=Sun)"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    secret = request.args.get('secret')
    if secret != 'cube2025reset':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from datetime import datetime, timedelta
        import pytz
        
        db = database.get_db()
        tz = pytz.timezone('Europe/Warsaw')
        now = datetime.now(tz)
        
        # Get data from last 30 days (same as get_daily_averages)
        start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        
        docs = db.collection('hourly_occupancy').where('date', '>=', start_date).stream()
        
        # Group by date, keep max per day (same logic as get_daily_averages)
        weekday_data = {}  # {date: max_occupancy}
        all_records = []
        
        for doc in docs:
            data = doc.to_dict()
            doc_weekday = data.get('weekday')
            date_str = data.get('date')
            occupancy = data.get('occupancy', 0)
            hour = data.get('hour')
            
            if doc_weekday == weekday and date_str:
                all_records.append({
                    'date': date_str,
                    'hour': hour,
                    'occupancy': occupancy
                })
                
                if date_str not in weekday_data:
                    weekday_data[date_str] = occupancy
                else:
                    weekday_data[date_str] = max(weekday_data[date_str], occupancy)
        
        # Calculate average
        values = list(weekday_data.values())
        avg = sum(values) / len(values) if values else 0
        
        # Get what the function returns
        averages = database.get_daily_averages()
        weekday_names = ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Nd']
        
        return jsonify({
            'weekday': weekday,
            'weekday_name': weekday_names[weekday],
            'date_range': f'{start_date} to {now.strftime("%Y-%m-%d")}',
            'days_with_data': len(weekday_data),
            'max_per_day': weekday_data,
            'all_values': values,
            'sum': sum(values) if values else 0,
            'calculated_average': round(avg, 1),
            'function_result': averages.get(weekday_names[weekday], 0),
            'total_records': len(all_records),
            'records_sample': sorted(all_records, key=lambda x: (x['date'], x['hour'] or 0))[-20:]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# EXPORT / BACKUP API ENDPOINTS
# =============================================================================

@app.route('/api/export/workouts')
def export_workouts():
    """Export all workouts as JSON"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    try:
        workouts = database.export_all_workouts()
        response = jsonify({
            'export_date': datetime.now().isoformat(),
            'count': len(workouts),
            'workouts': workouts
        })
        response.headers['Content-Disposition'] = 'attachment; filename=workouts_backup.json'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/full')
def export_full():
    """Export full backup of all data"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    try:
        backup = database.export_full_backup()
        response = jsonify(backup)
        response.headers['Content-Disposition'] = 'attachment; filename=gym_tracker_backup.json'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/strength')
def get_strength_stats():
    """Get strength statistics: PRs, volume, etc."""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        stats = database.get_strength_stats(user_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/progression/<part>')
def get_progression(part):
    """Get weight progression for a specific body part"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503
    
    user_id = request.args.get('user_id')
    
    try:
        progression = database.get_progression(part, user_id)
        return jsonify({
            'part': part,
            'data': progression,
            'config': database.BODY_PARTS.get(part, {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})



if __name__ == '__main__':
    # Initial fetch
    print("Starting CubeFitness Entries Tracker...")
    fetch_entries_data()
    
    # Run the server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)



