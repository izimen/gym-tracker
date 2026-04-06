"""Admin routes: user management, data reset, debug, export/backup."""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
import secrets
import pytz
import database
from extensions import FIRESTORE_ENABLED, ADMIN_SECRET, limiter

admin_bp = Blueprint('admin', __name__)


def _check_admin():
    """Verify admin secret. Returns error response or None if authorized."""
    secret = request.headers.get('X-Admin-Secret') or ''
    if not ADMIN_SECRET or not secrets.compare_digest(secret, ADMIN_SECRET):
        return jsonify({'error': 'Unauthorized'}), 401
    return None


@admin_bp.route('/api/admin/reset-password', methods=['POST'])
def admin_reset_password():
    """Admin: Reset a user's password"""
    if not FIRESTORE_ENABLED:
        return jsonify({'success': False, 'error': 'Firestore not available'}), 503

    err = _check_admin()
    if err:
        return err

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


@admin_bp.route('/api/admin/users')
def list_users():
    """Admin: List all users"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    err = _check_admin()
    if err:
        return err

    try:
        users = database.get_all_users()
        return jsonify({'users': users, 'count': len(users)})
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/admin/reset-hourly', methods=['DELETE'])
def reset_hourly_data():
    """Reset hourly occupancy data - clears all records to start fresh"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    err = _check_admin()
    if err:
        return err

    try:
        deleted_count = database.clear_hourly_occupancy()
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} hourly records',
            'deleted_count': deleted_count
        })
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/admin/debug-weekday/<int:weekday>')
def debug_weekday_data(weekday):
    """Debug: Analyze data for a specific weekday (0=Mon, 4=Fri, 6=Sun)"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    err = _check_admin()
    if err:
        return err

    try:
        db = database.get_db()
        tz = pytz.timezone('Europe/Warsaw')
        now = datetime.now(tz)

        start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')

        docs = db.collection('hourly_occupancy').where('date', '>=', start_date).stream()

        weekday_data = {}
        all_records = []

        for doc in docs:
            data = doc.to_dict()
            doc_weekday = data.get('weekday')
            date_str = data.get('date')
            occupancy = data.get('occupancy', 0)
            hour = data.get('hour')

            if doc_weekday == weekday and date_str:
                all_records.append({'date': date_str, 'hour': hour, 'occupancy': occupancy})
                if date_str not in weekday_data:
                    weekday_data[date_str] = occupancy
                else:
                    weekday_data[date_str] = max(weekday_data[date_str], occupancy)

        values = list(weekday_data.values())
        avg = sum(values) / len(values) if values else 0

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
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/export/workouts')
@limiter.limit("5 per hour")
def export_workouts():
    """Export all workouts as JSON (admin only)"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    err = _check_admin()
    if err:
        return err

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
        current_app.logger.error(f"Export error: {e}")
        return jsonify({'error': 'Export failed'}), 500


@admin_bp.route('/api/export/full')
@limiter.limit("5 per hour")
def export_full():
    """Export full backup of all data (admin only)"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    err = _check_admin()
    if err:
        return err

    try:
        backup = database.export_full_backup()
        response = jsonify(backup)
        response.headers['Content-Disposition'] = 'attachment; filename=gym_tracker_backup.json'
        return response
    except Exception as e:
        current_app.logger.error(f"Backup error: {e}")
        return jsonify({'error': 'Backup failed'}), 500
