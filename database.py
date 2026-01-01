"""
Firestore database module for storing gym entry history.
Uses Google Cloud Firestore for persistence on Cloud Run.
"""

from google.cloud import firestore
from datetime import datetime, timedelta
import pytz
import bcrypt
import re
import uuid
import os
import secrets

# Initialize Firestore client
db = None

def get_db():
    """Get or create Firestore client"""
    global db
    if db is None:
        db = firestore.Client()
    return db


# =============================================================================
# GYM HOURS CONFIGURATION
# =============================================================================
# CUSTOMIZATION: Modify these values to match your gym's operating hours.
# - 'weekday': tuple of (opening_hour, closing_hour-1) for Mon-Fri
# - 'weekend': tuple of (opening_hour, closing_hour-1) for Sat-Sun
# Hours are 0-23 (24-hour format). Last hour is when last slot STARTS.
# Example: (6, 22) means gym opens at 6:00 and last slot is 22:00-23:00

GYM_HOURS = {
    'weekday': (6, 22),  # Monday-Friday: 6:00 - 23:00
    'weekend': (8, 19),  # Saturday-Sunday: 8:00 - 20:00
}


def is_gym_open(weekday: int, hour: int) -> bool:
    """
    Check if gym is open at given weekday and hour.
    
    Args:
        weekday: 0=Monday, 6=Sunday
        hour: 0-23 (represents the start of the hour slot)
    
    Returns:
        True if gym is open, False otherwise
    """
    if weekday in (5, 6):  # Saturday, Sunday
        first, last = GYM_HOURS['weekend']
    else:  # Weekdays (Mon-Fri)
        first, last = GYM_HOURS['weekday']
    
    return first <= hour <= last


def is_complete_day(hours_data: dict, weekday: int) -> bool:
    """
    Check if a day has complete data (not a holiday/early closure).
    
    A day is INCOMPLETE if it has 4+ consecutive hours with zero occupancy,
    which suggests early closure or holiday hours.
    
    Args:
        hours_data: {hour: occupancy} dictionary for a single day
        weekday: 0=Monday, 6=Sunday
    
    Returns:
        True if day is complete and should be included in averages,
        False if day appears to be incomplete (holiday/early closure)
    """
    if not hours_data:
        return False
    
    # Get expected hours range based on weekday
    if weekday in (5, 6):  # Weekend
        first_hour, last_hour = GYM_HOURS['weekend']
    else:  # Weekday
        first_hour, last_hour = GYM_HOURS['weekday']
    
    expected_hours = set(range(first_hour, last_hour + 1))
    actual_hours = set(hours_data.keys())
    
    # If missing more than 3 expected hours, consider incomplete
    missing_hours = expected_hours - actual_hours
    if len(missing_hours) > 3:
        return False
    
    # Check for 4+ consecutive zeros (suggests early closure)
    sorted_hours = sorted(hours_data.keys())
    consecutive_zeros = 0
    max_consecutive_zeros = 0
    
    for hour in sorted_hours:
        occupancy = hours_data[hour]
        if occupancy == 0:
            consecutive_zeros += 1
            max_consecutive_zeros = max(max_consecutive_zeros, consecutive_zeros)
        else:
            consecutive_zeros = 0
    
    # 4+ consecutive zeros = likely early closure or holiday
    if max_consecutive_zeros >= 4:
        return False
    
    return True


# =============================================================================
# USER AUTHENTICATION
# =============================================================================

def validate_username(username: str) -> tuple:
    """
    Validate username.
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not username:
        return False, "Username is required"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 20:
        return False, "Username must be at most 20 characters"
    if not re.match(r'^[a-zA-Z0-9]+$', username):
        return False, "Username can only contain letters and digits"
    return True, None


def validate_password(password: str) -> tuple:
    """
    Validate password.
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not password:
        return False, "Password is required"
    if len(password) < 3:
        return False, "Password must be at least 3 characters"
    if len(password) > 20:
        return False, "Password must be at most 20 characters"
    return True, None


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def create_user(username: str, password: str) -> dict:
    """
    Create a new user.
    Returns: {'success': True, 'user_id': ..., 'username': ...} or {'success': False, 'error': ...}
    """
    # Validate inputs
    valid, error = validate_username(username)
    if not valid:
        return {'success': False, 'error': error}
    
    valid, error = validate_password(password)
    if not valid:
        return {'success': False, 'error': error}
    
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    
    # Check if username already exists (case-insensitive)
    username_lower = username.lower()
    existing = db.collection('users').where('username_lower', '==', username_lower).limit(1).stream()
    
    if any(True for _ in existing):
        return {'success': False, 'error': 'Username already taken'}
    
    # Create user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    
    db.collection('users').document(user_id).set({
        'user_id': user_id,
        'username': username,
        'username_lower': username_lower,
        'password_hash': password_hash,
        'created_at': datetime.now(tz).isoformat()
    })
    
    return {
        'success': True,
        'user_id': user_id,
        'username': username
    }


def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate a user.
    Returns: {'success': True, 'user_id': ..., 'username': ...} or {'success': False, 'error': ...}
    """
    if not username or not password:
        return {'success': False, 'error': 'Username and password required'}
    
    db = get_db()
    username_lower = username.lower()
    
    # Find user by username
    docs = db.collection('users').where('username_lower', '==', username_lower).limit(1).stream()
    
    user_doc = None
    for doc in docs:
        user_doc = doc.to_dict()
        break
    
    if not user_doc:
        return {'success': False, 'error': 'User not found'}
    
    # Verify password
    if not verify_password(password, user_doc.get('password_hash', '')):
        return {'success': False, 'error': 'Wrong password'}
    
    return {
        'success': True,
        'user_id': user_doc['user_id'],
        'username': user_doc['username']
    }


def admin_reset_password(username: str, new_password: str) -> dict:
    """
    Admin function to reset a user's password.
    Returns: {'success': True} or {'success': False, 'error': ...}
    """
    # Validate new password
    valid, error = validate_password(new_password)
    if not valid:
        return {'success': False, 'error': error}
    
    db = get_db()
    username_lower = username.lower()
    
    # Find user
    docs = db.collection('users').where('username_lower', '==', username_lower).limit(1).stream()
    
    user_doc = None
    doc_ref = None
    for doc in docs:
        user_doc = doc.to_dict()
        doc_ref = doc.reference
        break
    
    if not user_doc:
        return {'success': False, 'error': 'User not found'}
    
    # Update password
    new_hash = hash_password(new_password)
    doc_ref.update({'password_hash': new_hash})
    
    return {'success': True, 'username': user_doc['username']}


def get_all_users() -> list:
    """Get list of all users (for admin purposes). Returns list of {user_id, username, created_at}"""
    db = get_db()
    docs = db.collection('users').stream()
    
    users = []
    for doc in docs:
        data = doc.to_dict()
        users.append({
            'user_id': data.get('user_id'),
            'username': data.get('username'),
            'created_at': data.get('created_at')
        })
    
    return users


def save_daily_entry(entries_count: int):
    """
    Save or update today's entry count.
    Collection: daily_entries
    Document ID: YYYY-MM-DD (date string)
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d')
    
    doc_ref = db.collection('daily_entries').document(date_str)
    doc_ref.set({
        'date': date_str,
        'entries_count': entries_count,
        'last_updated': now.isoformat(),
        'weekday': now.weekday()  # 0=Monday, 6=Sunday
    })


def get_week_ago_entries() -> dict:
    """
    Get entry count from exactly 7 days ago.
    Returns: {'entries': int, 'date': str} or None
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    week_ago = datetime.now(tz) - timedelta(days=7)
    date_str = week_ago.strftime('%Y-%m-%d')
    
    doc = db.collection('daily_entries').document(date_str).get()
    if doc.exists:
        data = doc.to_dict()
        return {
            'entries': data.get('entries_count', 0),
            'date': date_str
        }
    return None


def get_average_for_weekday(weekday: int = None) -> float:
    """
    Calculate average entries for a specific weekday.
    weekday: 0=Monday, 6=Sunday. If None, uses current weekday.
    Returns: average as float rounded to 1 decimal
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    
    if weekday is None:
        weekday = datetime.now(tz).weekday()
    
    # Query all entries for this weekday
    docs = db.collection('daily_entries').where('weekday', '==', weekday).stream()
    
    entries = []
    for doc in docs:
        data = doc.to_dict()
        entries.append(data.get('entries_count', 0))
    
    if entries:
        return round(sum(entries) / len(entries), 1)
    return 0.0


def get_history_count() -> int:
    """
    Get total number of recorded days.
    Uses select() to minimize data transfer - only fetches document IDs.
    """
    db = get_db()
    # Use select([]) to only get document references without field data
    docs = db.collection('daily_entries').select([]).stream()
    return sum(1 for _ in docs)


WEEKDAY_NAMES_PL = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela']

def get_current_weekday_name() -> str:
    """Get current weekday name in Polish"""
    tz = pytz.timezone('Europe/Warsaw')
    weekday = datetime.now(tz).weekday()
    return WEEKDAY_NAMES_PL[weekday]


# =============================================================================
# WORKOUT TRACKING - Body Parts Calendar
# =============================================================================
# CUSTOMIZATION: Modify BODY_PARTS to customize workout categories.
# Each entry: 'key': {'name': 'Display Name', 'emoji': '🔥', 'color': '#HEX'}
# - key: Internal identifier (lowercase, no spaces)
# - name: Display name in UI (supports Unicode for any language)
# - emoji: Emoji shown in calendar/dashboard
# - color: Hex color for charts and highlights

# Default admin user ID - existing workouts belong to this user
DEFAULT_USER_ID = "admin"

BODY_PARTS = {
    'lydki': {'name': 'Łydki', 'emoji': '🚲', 'color': '#FF6B6B'},
    'uda': {'name': 'Uda', 'emoji': '🦵', 'color': '#4ECDC4'},
    'brzuch': {'name': 'Brzuch', 'emoji': '🔲', 'color': '#45B7D1'},
    'biceps': {'name': 'Biceps', 'emoji': '💪', 'color': '#96CEB4'},
    'triceps': {'name': 'Triceps', 'emoji': '🤸', 'color': '#FFEAA7'},
    'barki': {'name': 'Barki', 'emoji': '🏋️', 'color': '#DDA0DD'},
    'plecy': {'name': 'Plecy', 'emoji': '🔙', 'color': '#98D8C8'},
    'klata': {'name': 'Klata', 'emoji': '👕', 'color': '#F7DC6F'},
}


def ensure_admin_user():
    """
    Create admin user if it doesn't exist.
    Password is set via ADMIN_PASSWORD env var or generated securely.
    """
    db = get_db()
    # Check if admin exists
    docs = db.collection('users').where('username_lower', '==', 'admin').limit(1).stream()
    if not any(True for _ in docs):
        # Get password from env var or generate secure random password
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if not admin_password:
            admin_password = secrets.token_urlsafe(16)
            print(f"⚠️  SECURITY: Generated admin password: {admin_password}")
            print("   Set ADMIN_PASSWORD env var to use a custom password.")
        
        tz = pytz.timezone('Europe/Warsaw')
        password_hash = hash_password(admin_password)
        db.collection('users').document('admin').set({
            'user_id': 'admin',
            'username': 'admin',
            'username_lower': 'admin',
            'password_hash': password_hash,
            'created_at': datetime.now(tz).isoformat()
        })
        print("Created admin user.")


def save_workout(date_str: str, body_parts: list, weight_data: dict = None, notes: str = None, user_id: str = None):
    """
    Save a workout for a specific date.
    Collection: workouts
    Document ID: {user_id}_{date} for per-user storage
    
    weight_data format:
    {
        'klata': {'kg': 50, 'sets': 3, 'reps': 10},
        'biceps': {'kg': 15, 'sets': 4, 'reps': 12}
    }
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    # Use default user if not specified (backward compatibility)
    if not user_id:
        user_id = DEFAULT_USER_ID
    
    # Document ID includes user_id for separation
    doc_id = f"{user_id}_{date_str}"
    doc_ref = db.collection('workouts').document(doc_id)
    data = {
        'date': date_str,
        'user_id': user_id,
        'body_parts': body_parts,
        'created_at': now.isoformat(),
    }
    if weight_data:
        data['weight_data'] = weight_data
    if notes:
        data['notes'] = notes
    
    doc_ref.set(data)


def delete_workout(date_str: str, user_id: str = None):
    """Delete a workout for a specific date"""
    db = get_db()
    if not user_id:
        user_id = DEFAULT_USER_ID
    doc_id = f"{user_id}_{date_str}"
    db.collection('workouts').document(doc_id).delete()


def get_workout(date_str: str, user_id: str = None) -> dict:
    """Get workout for a specific date"""
    db = get_db()
    if not user_id:
        user_id = DEFAULT_USER_ID
    doc_id = f"{user_id}_{date_str}"
    doc = db.collection('workouts').document(doc_id).get()
    if doc.exists:
        return doc.to_dict()
    # Fallback: check old format (without user_id prefix) for backward compatibility
    if user_id == DEFAULT_USER_ID:
        doc = db.collection('workouts').document(date_str).get()
        if doc.exists:
            return doc.to_dict()
    return None


def get_month_workouts(year: int, month: int, user_id: str = None) -> list:
    """Get all workouts for a specific month"""
    db = get_db()
    if not user_id:
        user_id = DEFAULT_USER_ID
    
    # Create date range for the month
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month+1:02d}-01"
    
    # Query workouts for specific user
    docs = db.collection('workouts')\
        .where('date', '>=', start_date)\
        .where('date', '<', end_date)\
        .stream()
    
    workouts = []
    for doc in docs:
        data = doc.to_dict()
        # Include if user_id matches OR if no user_id set (old data, treat as admin)
        doc_user_id = data.get('user_id', DEFAULT_USER_ID)
        if doc_user_id == user_id:
            workouts.append(data)
    
    return workouts


def get_body_part_counts(year: int = None, month: int = None, user_id: str = None) -> dict:
    """
    Count how many times each body part was trained.
    If year/month provided, counts for that month only.
    Returns: {'klata': 5, 'plecy': 3, ...}
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    
    if year is None or month is None:
        now = datetime.now(tz)
        year = now.year
        month = now.month
    
    workouts = get_month_workouts(year, month, user_id)
    
    counts = {part: 0 for part in BODY_PARTS.keys()}
    for workout in workouts:
        for part in workout.get('body_parts', []):
            if part in counts:
                counts[part] += 1
    
    return counts


def get_weekly_workout_count(user_id: str = None) -> int:
    """Get number of workouts in the current calendar week (Monday-Sunday)"""
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    # Calculate current week's Monday and Sunday
    days_since_monday = now.weekday()  # Monday = 0, Sunday = 6
    week_start = now - timedelta(days=days_since_monday)  # This week's Monday
    week_end = week_start + timedelta(days=6)  # This week's Sunday
    
    if not user_id:
        user_id = DEFAULT_USER_ID
    
    start_date = week_start.strftime('%Y-%m-%d')
    end_date = week_end.strftime('%Y-%m-%d')
    
    docs = db.collection('workouts')\
        .where('date', '>=', start_date)\
        .where('date', '<=', end_date)\
        .stream()
    
    count = 0
    for doc in docs:
        data = doc.to_dict()
        doc_user_id = data.get('user_id', DEFAULT_USER_ID)
        if doc_user_id == user_id:
            count += 1
    return count


def get_monthly_workout_count(year: int = None, month: int = None, user_id: str = None) -> int:
    """Get number of workouts in a month"""
    tz = pytz.timezone('Europe/Warsaw')
    if year is None or month is None:
        now = datetime.now(tz)
        year = now.year
        month = now.month
    workouts = get_month_workouts(year, month, user_id)
    return len(workouts)


def get_neglected_parts(threshold: int = 2, user_id: str = None) -> list:
    """
    Find body parts that have been trained less than threshold times this month.
    Returns list of {'part': 'lydki', 'count': 1, 'name': 'Łydki'}
    """
    counts = get_body_part_counts(user_id=user_id)
    neglected = []
    
    for part, count in counts.items():
        if count < threshold:
            neglected.append({
                'part': part,
                'count': count,
                'name': BODY_PARTS[part]['name'],
                'emoji': BODY_PARTS[part]['emoji']
            })
    
    # Sort by count ascending (most neglected first)
    neglected.sort(key=lambda x: x['count'])
    return neglected


def get_most_trained_part(user_id: str = None) -> dict:
    """Get the most frequently trained body part this month"""
    counts = get_body_part_counts(user_id=user_id)
    if not counts:
        return None
    
    max_part = max(counts, key=counts.get)
    if counts[max_part] == 0:
        return None
    
    return {
        'part': max_part,
        'count': counts[max_part],
        'name': BODY_PARTS[max_part]['name'],
        'emoji': BODY_PARTS[max_part]['emoji']
    }


def get_last_workout(user_id: str = None) -> dict:
    """Get the most recent workout"""
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    today = datetime.now(tz).strftime('%Y-%m-%d')
    
    if not user_id:
        user_id = DEFAULT_USER_ID
    
    # Get workouts from last 30 days
    month_ago = (datetime.now(tz) - timedelta(days=30)).strftime('%Y-%m-%d')
    
    docs = db.collection('workouts')\
        .where('date', '>=', month_ago)\
        .where('date', '<=', today)\
        .order_by('date', direction=firestore.Query.DESCENDING)\
        .stream()
    
    for doc in docs:
        data = doc.to_dict()
        doc_user_id = data.get('user_id', DEFAULT_USER_ID)
        if doc_user_id == user_id:
            return data
    return None


def get_workout_dashboard_stats(user_id: str = None) -> dict:
    """Get all stats needed for the dashboard"""
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    return {
        'weekly_count': get_weekly_workout_count(user_id),
        'monthly_count': get_monthly_workout_count(user_id=user_id),
        'body_part_counts': get_body_part_counts(user_id=user_id),
        'neglected_parts': get_neglected_parts(threshold=3, user_id=user_id),
        'most_trained': get_most_trained_part(user_id),
        'last_workout': get_last_workout(user_id),
        'body_parts_config': BODY_PARTS,
        'current_month': now.month,
        'current_year': now.year
    }


# =============================================================================
# ADVANCED ANALYTICS - Charts and Heatmap
# =============================================================================

def get_weekly_workout_history(weeks: int = 12, user_id: str = None) -> list:
    """
    Get workout count for each of the last N weeks.
    Returns: [{"week": "2024-W49", "count": 5, "start_date": "2024-12-02"}, ...]
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    if not user_id:
        user_id = DEFAULT_USER_ID
    
    result = []
    
    for i in range(weeks - 1, -1, -1):
        # Calculate week start (Monday)
        days_since_monday = now.weekday()
        week_start = now - timedelta(days=days_since_monday + (i * 7))
        week_end = week_start + timedelta(days=6)
        
        start_str = week_start.strftime('%Y-%m-%d')
        end_str = week_end.strftime('%Y-%m-%d')
        
        # Query workouts in this week
        docs = db.collection('workouts')\
            .where('date', '>=', start_str)\
            .where('date', '<=', end_str)\
            .stream()
        
        count = 0
        for doc in docs:
            data = doc.to_dict()
            doc_user_id = data.get('user_id', DEFAULT_USER_ID)
            if doc_user_id == user_id:
                count += 1
        
        # Week number format (ISO week)
        week_num = week_start.isocalendar()[1]
        week_label = f"{week_start.year}-W{week_num:02d}"
        
        result.append({
            'week': week_label,
            'count': count,
            'start_date': start_str,
            'end_date': end_str
        })
    
    return result


def get_yearly_heatmap_data(year: int = None, user_id: str = None) -> dict:
    """
    Get workout intensity for each day of the year.
    Returns: {"2024-01-15": 3, "2024-01-16": 0, ...} (count of body parts trained)
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    
    if year is None:
        year = datetime.now(tz).year
    
    if not user_id:
        user_id = DEFAULT_USER_ID
    
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    docs = db.collection('workouts')\
        .where('date', '>=', start_date)\
        .where('date', '<=', end_date)\
        .stream()
    
    heatmap = {}
    for doc in docs:
        data = doc.to_dict()
        doc_user_id = data.get('user_id', DEFAULT_USER_ID)
        if doc_user_id == user_id:
            date_str = data.get('date')
            body_parts = data.get('body_parts', [])
            if date_str:
                heatmap[date_str] = len(body_parts)
    
    return {
        'year': year,
        'data': heatmap
    }


def get_month_comparison(user_id: str = None) -> dict:
    """
    Compare current month with previous month.
    Returns workout stats and percentage change.
    """
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    current_year = now.year
    current_month = now.month
    
    # Previous month
    if current_month == 1:
        prev_year = current_year - 1
        prev_month = 12
    else:
        prev_year = current_year
        prev_month = current_month - 1
    
    # Get counts
    current_count = get_monthly_workout_count(current_year, current_month, user_id)
    prev_count = get_monthly_workout_count(prev_year, prev_month, user_id)
    
    # Calculate days elapsed in current month
    days_in_current = now.day
    
    # Days in previous month
    if prev_month == 12:
        days_in_prev = 31
    else:
        days_in_prev = (datetime(prev_year, prev_month + 1, 1) - timedelta(days=1)).day
    
    # Calculate averages per week
    current_avg = round((current_count / days_in_current) * 7, 1) if days_in_current > 0 else 0
    prev_avg = round((prev_count / days_in_prev) * 7, 1) if days_in_prev > 0 else 0
    
    # Percentage change
    if prev_count > 0:
        change_percent = round(((current_count - prev_count) / prev_count) * 100, 1)
    else:
        change_percent = 100 if current_count > 0 else 0
    
    return {
        'current': {
            'year': current_year,
            'month': current_month,
            'month_name': ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec', 'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'][current_month - 1],
            'count': current_count,
            'days_elapsed': days_in_current,
            'avg_per_week': current_avg
        },
        'previous': {
            'year': prev_year,
            'month': prev_month,
            'month_name': ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec', 'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'][prev_month - 1],
            'count': prev_count,
            'days_total': days_in_prev,
            'avg_per_week': prev_avg
        },
        'change_percent': change_percent
    }


# =============================================================================
# HOURLY OCCUPANCY TRACKING - Best Hours Analysis
# =============================================================================

def save_hourly_occupancy(occupancy_count: int):
    """
    Save hourly occupancy data.
    Collection: hourly_occupancy
    Document ID: YYYY-MM-DD-HH (e.g., 2024-12-10-14)
    Only saves if it's a new hour (prevents duplicates within same hour)
    
    Gym hours:
    - Weekdays (Mon-Fri): 6:00 - 23:00
    - Weekends (Sat-Sun): 8:00 - 20:00
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    hour = now.hour
    weekday = now.weekday()
    
    # Check if gym is open - don't save data outside opening hours
    if not is_gym_open(weekday, hour):
        return  # Gym closed, don't save
    
    # Create document ID with date and hour
    doc_id = now.strftime('%Y-%m-%d-%H')
    date_str = now.strftime('%Y-%m-%d')
    
    doc_ref = db.collection('hourly_occupancy').document(doc_id)
    
    # Only save if document doesn't exist or update with latest value
    doc_ref.set({
        'date': date_str,
        'hour': hour,
        'weekday': weekday,
        'occupancy': occupancy_count,
        'timestamp': now.isoformat()
    }, merge=True)


def get_hourly_averages(days: int = 30) -> dict:
    """
    Calculate average ENTRIES per hour of the day.
    Entries = difference between consecutive hourly readings.
    Uses data from the last N days.
    
    Gym hours:
    - Weekdays (Mon-Fri): 6:00 - 23:00
    - Weekends (Sat-Sun): 8:00 - 20:00
    
    Returns: {6: 12.5, 7: 18.3, ..., 22: 8.2}
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    # Get start date
    start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d')
    
    # Query all hourly data from start date
    docs = db.collection('hourly_occupancy')\
        .where('date', '>=', start_date)\
        .stream()
    
    # Group data by date, then by hour
    # Structure: {date: {hour: (occupancy, weekday)}}
    daily_hourly_data = {}
    
    for doc in docs:
        data = doc.to_dict()
        date_str = data.get('date')
        hour = data.get('hour')
        weekday = data.get('weekday')
        occupancy = data.get('occupancy', 0)
        
        if date_str and hour is not None and weekday is not None:
            # Filter hours based on gym opening times
            if not is_gym_open(weekday, hour):
                continue  # Skip hours outside gym hours
            
            if date_str not in daily_hourly_data:
                daily_hourly_data[date_str] = {}
            daily_hourly_data[date_str][hour] = (occupancy, weekday)
    
    # Calculate entries per hour (difference between consecutive readings)
    hourly_entries = {}
    for h in range(6, 23):  # 6 AM to 10 PM (last slot 22:00-23:00)
        hourly_entries[h] = []
    
    for date_str, hours_data in daily_hourly_data.items():
        sorted_hours = sorted(hours_data.keys())
        
        # Get weekday from first hour's data
        if not sorted_hours:
            continue
        _, weekday = hours_data[sorted_hours[0]]
        
        # Convert to simple {hour: occupancy} format for is_complete_day check
        simple_hours_data = {h: occ for h, (occ, _) in hours_data.items()}
        
        # Skip incomplete days (holidays, early closures)
        if not is_complete_day(simple_hours_data, weekday):
            continue
        
        for i, hour in enumerate(sorted_hours):
            occupancy, weekday = hours_data[hour]
            
            if i == 0:
                # First hour of the day - use raw value as entries
                entries = occupancy
            else:
                prev_hour = sorted_hours[i - 1]
                prev_occupancy, _ = hours_data[prev_hour]
                # Entries = current reading - previous reading
                entries = occupancy - prev_occupancy
                # If negative (e.g., counter reset), set to 0
                if entries < 0:
                    entries = 0
            
            hourly_entries[hour].append(entries)
    
    # Calculate averages
    averages = {}
    for hour, values in hourly_entries.items():
        if values:
            averages[hour] = round(sum(values) / len(values), 1)
        else:
            averages[hour] = 0
    
    return averages



def get_best_hours(top_n: int = 3) -> list:
    """
    Get the N best hours with lowest average occupancy.
    Returns: [{'hour': 6, 'avg': 5.2, 'label': '6:00'}, ...]
    """
    averages = get_hourly_averages()
    
    # Filter out hours with no data (avg = 0 means no data)
    hours_with_data = [(h, avg) for h, avg in averages.items() if avg > 0]
    
    if not hours_with_data:
        # No data yet, return default suggestions
        return [
            {'hour': 6, 'avg': 0, 'label': '6:00', 'no_data': True},
            {'hour': 14, 'avg': 0, 'label': '14:00', 'no_data': True},
            {'hour': 21, 'avg': 0, 'label': '21:00', 'no_data': True}
        ]
    
    # Sort by average (lowest first)
    sorted_hours = sorted(hours_with_data, key=lambda x: x[1])
    
    best = []
    for hour, avg in sorted_hours[:top_n]:
        best.append({
            'hour': hour,
            'avg': avg,
            'label': f'{hour}:00'
        })
    
    return best


def get_hourly_stats() -> dict:
    """
    Get complete hourly statistics for the chart.
    Returns averages, best hours, and data quality info.
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    averages = get_hourly_averages()
    best_hours = get_best_hours(3)
    
    # Count total data points
    start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    docs = db.collection('hourly_occupancy')\
        .where('date', '>=', start_date)\
        .select([])\
        .stream()
    data_points = sum(1 for _ in docs)
    
    # Estimate days with data
    days_with_data = data_points // 17 if data_points > 0 else 0  # ~17 hours per day (6-22)
    
    return {
        'hourly_averages': averages,
        'best_hours': best_hours,
        'data_points': data_points,
        'days_with_data': days_with_data,
        'current_hour': now.hour
    }


# =============================================================================
# EXTENDED OCCUPANCY STATISTICS
# =============================================================================

WEEKDAY_NAMES_SHORT = ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Nd']


def get_daily_averages(days: int = 30) -> dict:
    """
    Calculate average occupancy for each day of the week.
    Uses data from the last N days.
    Excludes incomplete days (holidays, early closures).
    
    Gym hours:
    - Weekdays (Mon-Fri): 6:00 - 23:00
    - Weekends (Sat-Sun): 8:00 - 20:00
    
    Returns: {'Pon': 45.2, 'Wt': 52.1, ..., 'Nd': 28.5}
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d')
    
    docs = db.collection('hourly_occupancy')\
        .where('date', '>=', start_date)\
        .stream()
    
    # First, group all data by date: {date: {hour: (occupancy, weekday)}}
    all_daily_data = {}
    
    for doc in docs:
        data = doc.to_dict()
        weekday = data.get('weekday')
        date_str = data.get('date')
        hour = data.get('hour')
        occupancy = data.get('occupancy', 0)
        
        if weekday is not None and date_str and hour is not None:
            # Filter hours based on gym opening times
            if not is_gym_open(weekday, hour):
                continue
            
            if date_str not in all_daily_data:
                all_daily_data[date_str] = {}
            all_daily_data[date_str][hour] = (occupancy, weekday)
    
    # Now filter for complete days and calculate max per day
    daily_data = {i: {} for i in range(7)}  # {weekday: {date: max_occupancy}}
    
    for date_str, hours_data in all_daily_data.items():
        if not hours_data:
            continue
        
        # Get weekday from first entry
        first_hour = next(iter(hours_data.keys()))
        _, weekday = hours_data[first_hour]
        
        # Convert to simple format for is_complete_day check
        simple_hours_data = {h: occ for h, (occ, _) in hours_data.items()}
        
        # Skip incomplete days
        if not is_complete_day(simple_hours_data, weekday):
            continue
        
        # Calculate max occupancy for this complete day
        max_occupancy = max(occ for occ, _ in hours_data.values())
        daily_data[weekday][date_str] = max_occupancy
    
    # Calculate averages for each weekday
    averages = {}
    for weekday in range(7):
        values = list(daily_data[weekday].values())
        if values:
            averages[WEEKDAY_NAMES_SHORT[weekday]] = round(sum(values) / len(values), 1)
        else:
            averages[WEEKDAY_NAMES_SHORT[weekday]] = 0
    
    return averages


def get_week_ago_same_hour() -> dict:
    """
    Get occupancy from exactly 7 days ago at the same hour.
    Returns: {'occupancy': int, 'date': str, 'hour': int} or None
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    week_ago = now - timedelta(days=7)
    
    doc_id = week_ago.strftime('%Y-%m-%d-%H')
    doc = db.collection('hourly_occupancy').document(doc_id).get()
    
    if doc.exists:
        data = doc.to_dict()
        return {
            'occupancy': data.get('occupancy', 0),
            'date': data.get('date'),
            'hour': data.get('hour')
        }
    return None


def get_best_day_hour_combos(top_n: int = 3) -> list:
    """
    Get the N best day+hour combinations with lowest average entries.
    Uses sliding 2-hour windows (6-8, 7-9, 8-10, ..., 21-23) for analysis.
    Returns: [{'weekday': 'Śr', 'start_hour': 6, 'avg': 8.2, 'label': 'Śr 6:00-8:00'}, ...]
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    
    docs = db.collection('hourly_occupancy')\
        .where('date', '>=', start_date)\
        .stream()
    
    # Group data by date
    daily_data = {}
    
    for doc in docs:
        data = doc.to_dict()
        date_str = data.get('date')
        hour = data.get('hour')
        weekday = data.get('weekday')
        occupancy = data.get('occupancy', 0)
        
        if date_str and hour is not None and weekday is not None and is_gym_open(weekday, hour):
            if date_str not in daily_data:
                daily_data[date_str] = {}
            daily_data[date_str][hour] = (occupancy, weekday)
    
    # Calculate entries per hour for each day (only complete days)
    daily_hourly_entries = {}  # {date: {hour: (entries, weekday)}}
    
    for date_str, hours_data in daily_data.items():
        sorted_hours = sorted(hours_data.keys())
        if not sorted_hours:
            continue
        
        # Get weekday from first hour's data
        _, weekday = hours_data[sorted_hours[0]]
        
        # Convert to simple format for is_complete_day check
        simple_hours_data = {h: occ for h, (occ, _) in hours_data.items()}
        
        # Skip incomplete days (holidays, early closures)
        if not is_complete_day(simple_hours_data, weekday):
            continue
        
        daily_hourly_entries[date_str] = {}
        
        for i, hour in enumerate(sorted_hours):
            occupancy, weekday = hours_data[hour]
            if i == 0:
                entries = occupancy
            else:
                prev_hour = sorted_hours[i - 1]
                prev_occupancy, _ = hours_data[prev_hour]
                entries = occupancy - prev_occupancy
                if entries < 0:
                    entries = 0
            
            daily_hourly_entries[date_str][hour] = (entries, weekday)
    
    # Calculate sliding 2-hour window sums for each weekday
    # Windows: 6-8, 7-9, 8-10, ..., 21-23
    window_data = {}  # {(weekday, start_hour): [2-hour sums]}
    
    for date_str, hourly_data in daily_hourly_entries.items():
        # Get weekday from any hour in this day's data
        first_hour = next(iter(hourly_data.keys()), None)
        if first_hour is None:
            continue
        _, weekday = hourly_data[first_hour]
        
        # Check each possible 2-hour window
        for start_hour in range(6, 22):  # 6-8 through 21-23
            end_hour = start_hour + 2
            if end_hour > 23:
                end_hour = 23
            
            # Sum entries for hours in this window
            window_sum = 0
            hours_in_window = 0
            for h in range(start_hour, end_hour):
                if h in hourly_data:
                    entries, _ = hourly_data[h]
                    window_sum += entries
                    hours_in_window += 1
            
            # Only add if we have data for at least 1 hour in the window
            if hours_in_window > 0:
                key = (weekday, start_hour)
                if key not in window_data:
                    window_data[key] = []
                window_data[key].append(window_sum)
    
    # Calculate averages for each window
    averages = []
    for (weekday, start_hour), values in window_data.items():
        if values:
            # Skip weekend hours outside gym opening hours (8:00-20:00)
            # Saturday=5, Sunday=6 - gym closed before 8:00 and after 20:00
            if weekday in (5, 6):
                end_hour = min(start_hour + 2, 23)
                # Skip if window starts before 8:00 or ends after 20:00
                if start_hour < 8 or end_hour > 20:
                    continue
            
            avg = sum(values) / len(values)
            end_hour = min(start_hour + 2, 23)
            averages.append({
                'weekday': weekday,
                'weekday_name': WEEKDAY_NAMES_SHORT[weekday],
                'start_hour': start_hour,
                'end_hour': end_hour,
                'avg': round(avg, 1),
                'label': f"{WEEKDAY_NAMES_SHORT[weekday]} {start_hour}:00-{end_hour}:00"
            })
    
    # Sort by average (lowest first = best)
    averages.sort(key=lambda x: x['avg'])
    
    return averages[:top_n]



def get_worst_day_hour_combos(top_n: int = 3) -> list:
    """
    Get the N worst day+hour combinations with highest average entries.
    Uses sliding 2-hour windows (6-8, 7-9, 8-10, ..., 21-23) for analysis.
    Returns same format as get_best_day_hour_combos but sorted highest first.
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    
    docs = db.collection('hourly_occupancy')\
        .where('date', '>=', start_date)\
        .stream()
    
    # Group data by date
    daily_data = {}
    
    for doc in docs:
        data = doc.to_dict()
        date_str = data.get('date')
        hour = data.get('hour')
        weekday = data.get('weekday')
        occupancy = data.get('occupancy', 0)
        
        if date_str and hour is not None and weekday is not None and is_gym_open(weekday, hour):
            if date_str not in daily_data:
                daily_data[date_str] = {}
            daily_data[date_str][hour] = (occupancy, weekday)
    
    # Calculate entries per hour for each day (only complete days)
    daily_hourly_entries = {}  # {date: {hour: (entries, weekday)}}
    
    for date_str, hours_data in daily_data.items():
        sorted_hours = sorted(hours_data.keys())
        if not sorted_hours:
            continue
        
        # Get weekday from first hour's data
        _, weekday = hours_data[sorted_hours[0]]
        
        # Convert to simple format for is_complete_day check
        simple_hours_data = {h: occ for h, (occ, _) in hours_data.items()}
        
        # Skip incomplete days (holidays, early closures)
        if not is_complete_day(simple_hours_data, weekday):
            continue
        
        daily_hourly_entries[date_str] = {}
        
        for i, hour in enumerate(sorted_hours):
            occupancy, weekday = hours_data[hour]
            if i == 0:
                entries = occupancy
            else:
                prev_hour = sorted_hours[i - 1]
                prev_occupancy, _ = hours_data[prev_hour]
                entries = occupancy - prev_occupancy
                if entries < 0:
                    entries = 0
            
            daily_hourly_entries[date_str][hour] = (entries, weekday)
    
    # Calculate sliding 2-hour window sums for each weekday
    window_data = {}  # {(weekday, start_hour): [2-hour sums]}
    
    for date_str, hourly_data in daily_hourly_entries.items():
        first_hour = next(iter(hourly_data.keys()), None)
        if first_hour is None:
            continue
        _, weekday = hourly_data[first_hour]
        
        # Check each possible 2-hour window
        for start_hour in range(6, 22):  # 6-8 through 21-23
            end_hour = start_hour + 2
            if end_hour > 23:
                end_hour = 23
            
            # Sum entries for hours in this window
            window_sum = 0
            hours_in_window = 0
            for h in range(start_hour, end_hour):
                if h in hourly_data:
                    entries, _ = hourly_data[h]
                    window_sum += entries
                    hours_in_window += 1
            
            if hours_in_window > 0:
                key = (weekday, start_hour)
                if key not in window_data:
                    window_data[key] = []
                window_data[key].append(window_sum)
    
    # Calculate averages for each window
    averages = []
    for (weekday, start_hour), values in window_data.items():
        if values:
            # Skip weekend hours outside gym opening hours (8:00-20:00)
            # Saturday=5, Sunday=6 - gym closed before 8:00 and after 20:00
            if weekday in (5, 6):
                end_hour = min(start_hour + 2, 23)
                # Skip if window starts before 8:00 or ends after 20:00
                if start_hour < 8 or end_hour > 20:
                    continue
            
            avg = sum(values) / len(values)
            end_hour = min(start_hour + 2, 23)
            averages.append({
                'weekday': weekday,
                'weekday_name': WEEKDAY_NAMES_SHORT[weekday],
                'start_hour': start_hour,
                'end_hour': end_hour,
                'avg': round(avg, 1),
                'label': f"{WEEKDAY_NAMES_SHORT[weekday]} {start_hour}:00-{end_hour}:00"
            })
    
    # Sort by average (highest first = worst)
    averages.sort(key=lambda x: x['avg'], reverse=True)
    
    return averages[:top_n]



def get_current_hour_average() -> float:
    """Get average occupancy for the current hour across all days."""
    tz = pytz.timezone('Europe/Warsaw')
    current_hour = datetime.now(tz).hour
    
    averages = get_hourly_averages()
    return averages.get(current_hour, 0)


def get_today_average() -> float:
    """Get average MAX occupancy for today's weekday."""
    tz = pytz.timezone('Europe/Warsaw')
    current_weekday = datetime.now(tz).weekday()
    
    averages = get_daily_averages()
    weekday_name = WEEKDAY_NAMES_SHORT[current_weekday]
    return averages.get(weekday_name, 0)


def get_weekday_hour_average(weekday: int, hour: int, days: int = 30) -> float:
    """
    Get average occupancy for a specific weekday and hour.
    For example: average Friday at 17:00.
    
    Note: We query by date only and filter weekday/hour in memory
    to avoid needing a composite Firestore index.
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d')
    
    # Query only by date to avoid composite index requirement
    docs = db.collection('hourly_occupancy')\
        .where('date', '>=', start_date)\
        .stream()
    
    values = []
    for doc in docs:
        data = doc.to_dict()
        doc_weekday = data.get('weekday')
        doc_hour = data.get('hour')
        
        # Filter by weekday and hour in memory
        if doc_weekday == weekday and doc_hour == hour:
            occupancy = data.get('occupancy', 0)
            values.append(occupancy)
    
    if values:
        return round(sum(values) / len(values), 1)
    return 0


def get_extended_occupancy_stats() -> dict:
    """
    Get all extended occupancy statistics for the dashboard.
    """
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    # Calculate weekday-hour average (e.g., average Friday at 17:00)
    today_hour_avg = get_weekday_hour_average(now.weekday(), now.hour)
    
    return {
        # Current info
        'current_weekday': WEEKDAY_NAMES_SHORT[now.weekday()],
        'current_hour': now.hour,
        
        # Averages
        'daily_averages': get_daily_averages(),
        'hourly_averages': get_hourly_averages(),
        'current_hour_avg': get_current_hour_average(),  # All days, this hour
        'today_avg': get_today_average(),  # This weekday, MAX daily
        'today_hour_avg': today_hour_avg,  # This weekday, this hour
        
        # Best/Worst combos
        'best_times': get_best_day_hour_combos(3),
        'worst_times': get_worst_day_hour_combos(3),
        
        # Current weekday average for display
        'weekday_name_full': WEEKDAY_NAMES_PL[now.weekday()],
    }


# =============================================================================
# ADMIN FUNCTIONS - Data Management
# =============================================================================

def clear_hourly_occupancy() -> int:
    """
    Delete all documents from the hourly_occupancy collection.
    Returns the number of deleted documents.
    Use with caution - this permanently removes all hourly data!
    """
    db = get_db()
    docs = db.collection('hourly_occupancy').stream()
    
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    
    return deleted


# =============================================================================
# DATA EXPORT - Backup Functions
# =============================================================================

def export_all_workouts() -> list:
    """
    Export all workouts for backup.
    Returns list of all workout documents.
    """
    db = get_db()
    docs = db.collection('workouts').stream()
    
    workouts = []
    for doc in docs:
        workouts.append(doc.to_dict())
    
    return workouts


def export_all_entries() -> list:
    """
    Export all daily entries for backup.
    Returns list of all entry documents.
    """
    db = get_db()
    docs = db.collection('daily_entries').stream()
    
    entries = []
    for doc in docs:
        entries.append(doc.to_dict())
    
    return entries


def export_full_backup() -> dict:
    """
    Create a full backup of all data.
    Returns complete backup as a dictionary.
    """
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    return {
        'backup_date': now.isoformat(),
        'backup_type': 'full',
        'workouts': export_all_workouts(),
        'daily_entries': export_all_entries(),
        'body_parts_config': BODY_PARTS
    }


# =============================================================================
# PERSONAL RECORDS & PROGRESSION
# =============================================================================

def get_personal_records(user_id: str = None):
    """
    Get personal records (max weight) for each body part.
    Returns dict with max kg, date, and details for each part.
    """
    db = get_db()
    
    if not user_id:
        user_id = DEFAULT_USER_ID
    
    docs = db.collection('workouts').stream()
    
    records = {}
    
    for doc in docs:
        data = doc.to_dict()
        # Filter by user_id
        doc_user_id = data.get('user_id', DEFAULT_USER_ID)
        if doc_user_id != user_id:
            continue
        
        weight_data = data.get('weight_data', {})
        date = data.get('date', '')
        
        for part, details in weight_data.items():
            kg = details.get('kg', 0)
            if kg > 0:
                if part not in records or kg > records[part]['kg']:
                    records[part] = {
                        'kg': kg,
                        'sets': details.get('sets', 0),
                        'reps': details.get('reps', 0),
                        'date': date,
                        'name': BODY_PARTS.get(part, {}).get('name', part),
                        'emoji': BODY_PARTS.get(part, {}).get('emoji', '')
                    }
    
    return records


def get_progression(body_part: str, user_id: str = None, limit: int = 20):
    """
    Get weight progression over time for a specific body part.
    Returns list of {date, kg, sets, reps} sorted by date.
    """
    db = get_db()
    
    if not user_id:
        user_id = DEFAULT_USER_ID
    
    docs = db.collection('workouts').order_by('date').stream()
    
    progression = []
    
    for doc in docs:
        data = doc.to_dict()
        # Filter by user_id
        doc_user_id = data.get('user_id', DEFAULT_USER_ID)
        if doc_user_id != user_id:
            continue
        
        weight_data = data.get('weight_data', {})
        
        if body_part in weight_data:
            details = weight_data[body_part]
            kg = details.get('kg', 0)
            if kg > 0:
                progression.append({
                    'date': data.get('date', ''),
                    'kg': kg,
                    'sets': details.get('sets', 0),
                    'reps': details.get('reps', 0)
                })
    
    # Return last N entries
    return progression[-limit:] if len(progression) > limit else progression


def get_strength_stats(user_id: str = None):
    """
    Get combined strength statistics for the Siła tab.
    """
    records = get_personal_records(user_id)
    
    # Calculate total volume this month
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    month_workouts = get_month_workouts(now.year, now.month, user_id)
    
    total_volume = 0
    for workout in month_workouts:
        weight_data = workout.get('weight_data', {})
        for part, details in weight_data.items():
            kg = details.get('kg', 0)
            sets = details.get('sets', 0)
            reps = details.get('reps', 0)
            total_volume += kg * sets * reps
    
    return {
        'records': records,
        'monthly_volume': total_volume,
        'body_parts_config': BODY_PARTS
    }


# =============================================================================
# NEW YEAR EFFECT STATISTICS
# =============================================================================

def get_month_daily_max_data(year: int, month: int) -> dict:
    """
    Get daily max occupancy data for a specific month.
    Only includes complete days (excludes holidays/early closures).
    
    Returns: {
        'daily_max': {date_str: max_occupancy},
        'weekday_max': {weekday: [max_values]},
        'average': float,
        'peak_day': {date, occupancy}
    }
    """
    db = get_db()
    
    # Date range for the month
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month+1:02d}-01"
    
    # Query all hourly data for the month
    docs = db.collection('hourly_occupancy')\
        .where('date', '>=', start_date)\
        .where('date', '<', end_date)\
        .stream()
    
    # Group by date: {date: {hour: (occupancy, weekday)}}
    daily_data = {}
    
    for doc in docs:
        data = doc.to_dict()
        date_str = data.get('date')
        hour = data.get('hour')
        weekday = data.get('weekday')
        occupancy = data.get('occupancy', 0)
        
        if date_str and hour is not None and weekday is not None:
            # Filter hours based on gym opening times
            if not is_gym_open(weekday, hour):
                continue
            
            if date_str not in daily_data:
                daily_data[date_str] = {}
            daily_data[date_str][hour] = (occupancy, weekday)
    
    # Process complete days only
    daily_max = {}
    weekday_max = {i: [] for i in range(7)}
    peak_day = {'date': None, 'occupancy': 0}
    
    for date_str, hours_data in daily_data.items():
        if not hours_data:
            continue
        
        # Get weekday from first entry
        first_hour = next(iter(hours_data.keys()))
        _, weekday = hours_data[first_hour]
        
        # Convert to simple format for completeness check
        simple_hours_data = {h: occ for h, (occ, _) in hours_data.items()}
        
        # Skip incomplete days
        if not is_complete_day(simple_hours_data, weekday):
            continue
        
        # Calculate max occupancy for this day
        max_occ = max(occ for occ, _ in hours_data.values())
        daily_max[date_str] = max_occ
        weekday_max[weekday].append(max_occ)
        
        # Track peak day
        if max_occ > peak_day['occupancy']:
            peak_day = {'date': date_str, 'occupancy': max_occ}
    
    # Calculate average
    values = list(daily_max.values())
    average = round(sum(values) / len(values), 1) if values else 0
    
    return {
        'daily_max': daily_max,
        'weekday_max': weekday_max,
        'average': average,
        'peak_day': peak_day if peak_day['date'] else None,
        'days_count': len(values)
    }


def get_january_weekly_trend(year: int) -> list:
    """
    Get weekly averages for January to track the decay of New Year's resolutions.
    
    Returns: [
        {'week': 1, 'avg': 156, 'percent': 100},
        {'week': 2, 'avg': 148, 'percent': 95, 'change': -5},
        ...
    ]
    """
    db = get_db()
    tz = pytz.timezone('Europe/Warsaw')
    
    # Get all January data
    start_date = f"{year}-01-01"
    end_date = f"{year}-02-01"
    
    docs = db.collection('hourly_occupancy')\
        .where('date', '>=', start_date)\
        .where('date', '<', end_date)\
        .stream()
    
    # Group by date
    daily_data = {}
    for doc in docs:
        data = doc.to_dict()
        date_str = data.get('date')
        hour = data.get('hour')
        weekday = data.get('weekday')
        occupancy = data.get('occupancy', 0)
        
        if date_str and hour is not None and weekday is not None:
            if not is_gym_open(weekday, hour):
                continue
            if date_str not in daily_data:
                daily_data[date_str] = {}
            daily_data[date_str][hour] = (occupancy, weekday)
    
    # Calculate max per complete day and assign to week
    week_data = {1: [], 2: [], 3: [], 4: [], 5: []}
    
    for date_str, hours_data in daily_data.items():
        if not hours_data:
            continue
        
        first_hour = next(iter(hours_data.keys()))
        _, weekday = hours_data[first_hour]
        simple_hours_data = {h: occ for h, (occ, _) in hours_data.items()}
        
        if not is_complete_day(simple_hours_data, weekday):
            continue
        
        max_occ = max(occ for occ, _ in hours_data.values())
        
        # Determine week number (1-5)
        day = int(date_str.split('-')[2])
        week_num = min((day - 1) // 7 + 1, 5)
        week_data[week_num].append(max_occ)
    
    # Build result
    result = []
    baseline = None
    prev_percent = None
    
    for week in range(1, 6):
        values = week_data[week]
        if not values:
            continue
        
        avg = round(sum(values) / len(values), 1)
        
        if baseline is None:
            baseline = avg
            percent = 100
            change = 0
        else:
            percent = round((avg / baseline) * 100, 1) if baseline > 0 else 0
            change = round(percent - prev_percent, 1) if prev_percent else 0
        
        result.append({
            'week': week,
            'avg': avg,
            'percent': percent,
            'change': change,
            'days': len(values)
        })
        prev_percent = percent
    
    return result


def get_new_year_effect(year: int = None) -> dict:
    """
    Calculate New Year's resolution effect statistics.
    Compares January attendance with December.
    Returns realistic mock data if not enough real data is available.
    """
    WEEKDAY_NAMES_PL = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela']
    tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(tz)
    
    if year is None:
        # If we're in December, we are interested in the UPCOMING January (next year)
        if now.month == 12:
            year = now.year + 1
        else:
            year = now.year
    
    # Get December data (previous year relative to the target January)
    dec_year = year - 1
    dec_data = get_month_daily_max_data(dec_year, 12)
    
    # Get January data
    jan_data = get_month_daily_max_data(year, 1)
    
    # Check if we have enough data (need at least 3 days in both months)
    if dec_data['days_count'] < 3 or jan_data['days_count'] < 3:
        return {'has_data': False, 'reason': 'Za mało danych'}
    
    # Calculate overall change
    if dec_data['average'] > 0:
        overall_change = round(((jan_data['average'] - dec_data['average']) / dec_data['average']) * 100, 1)
    else:
        overall_change = 0
    
    # Calculate weekday averages and changes
    dec_weekday_avg = {}
    jan_weekday_avg = {}
    weekday_changes = {}
    
    for wd in range(7):
        dec_vals = dec_data['weekday_max'][wd]
        jan_vals = jan_data['weekday_max'][wd]
        
        dec_avg = round(sum(dec_vals) / len(dec_vals), 1) if dec_vals else 0
        jan_avg = round(sum(jan_vals) / len(jan_vals), 1) if jan_vals else 0
        
        dec_weekday_avg[wd] = dec_avg
        jan_weekday_avg[wd] = jan_avg
        
        if dec_avg > 0:
            weekday_changes[wd] = round(((jan_avg - dec_avg) / dec_avg) * 100, 1)
        else:
            weekday_changes[wd] = 0
    
    # Current weekday comparison
    current_weekday = now.weekday()
    current_weekday_change = weekday_changes.get(current_weekday, 0)
    
    # Weekly trend
    weekly_trend = get_january_weekly_trend(year)
    
    # Calculate average weekly decay
    if len(weekly_trend) >= 2:
        total_decay = weekly_trend[-1]['percent'] - weekly_trend[0]['percent']
        weeks_span = len(weekly_trend) - 1
        avg_weekly_decay = round(total_decay / weeks_span, 1) if weeks_span > 0 else 0
    else:
        avg_weekly_decay = 0
    
    return {
        'has_data': True,
        'december': {
            'average': dec_data['average'],
            'peak_day': dec_data['peak_day'],
            'days_count': dec_data['days_count'],
            'weekday_avg': dec_weekday_avg
        },
        'january': {
            'average': jan_data['average'],
            'peak_day': jan_data['peak_day'],
            'days_count': jan_data['days_count'],
            'weekday_avg': jan_weekday_avg
        },
        'overall_change': overall_change,
        'weekday_changes': weekday_changes,
        'current_weekday': current_weekday,
        'current_weekday_name': WEEKDAY_NAMES_PL[current_weekday],
        'current_weekday_change': current_weekday_change,
        'weekly_trend': weekly_trend,
        'avg_weekly_decay': avg_weekly_decay
    }
