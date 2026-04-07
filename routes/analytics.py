"""Analytics routes: weekly, heatmap, comparison, best-hours, extended, new-year, completeness, debug."""

from flask import Blueprint, jsonify, request, current_app
from datetime import date as dt_date
import re
import secrets
import database
import extensions

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/api/analytics/weekly')
@extensions.limiter.limit("30 per minute")
def get_analytics_weekly():
    """Get weekly workout history for the last 12 weeks"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = extensions.require_login()
    if err:
        return err

    try:
        data = database.get_weekly_workout_history(weeks=12, user_id=user_id)
        return jsonify({'weeks': data})
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/api/analytics/heatmap/<int:year>')
@extensions.limiter.limit("30 per minute")
def get_analytics_heatmap(year):
    """Get yearly heatmap data"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    if not (2020 <= year <= 2100):
        return jsonify({'error': 'Invalid year'}), 400

    user_id, err = extensions.require_login()
    if err:
        return err

    try:
        data = database.get_yearly_heatmap_data(year, user_id)
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/api/analytics/comparison')
@extensions.limiter.limit("30 per minute")
def get_analytics_comparison():
    """Get month-to-month comparison"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = extensions.require_login()
    if err:
        return err

    try:
        data = database.get_month_comparison(user_id)
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/api/analytics/best-hours')
@extensions.limiter.limit("30 per minute")
def get_analytics_best_hours():
    """Get best gym hours analysis"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = extensions.require_login()
    if err:
        return err

    try:
        data = database.get_hourly_stats()
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/api/analytics/extended')
@extensions.limiter.limit("100 per hour")
def get_analytics_extended():
    """Get extended occupancy statistics for the dashboard"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = extensions.require_login()
    if err:
        return err

    try:
        data = database.get_extended_occupancy_stats()
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/api/analytics/new-year')
@extensions.limiter.limit("100 per hour")
def get_new_year_stats():
    """Get New Year's resolution effect statistics"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = extensions.require_login()
    if err:
        return err

    try:
        year = request.args.get('year', type=int)
        data = database.get_new_year_effect(year)
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/api/analytics/completeness/<int:year>/<int:month>')
@extensions.limiter.limit("30 per minute")
def get_data_completeness(year, month):
    """Get data collection completeness status for each day of a month"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    if not (2020 <= year <= 2100) or not (1 <= month <= 12):
        return jsonify({'error': 'Invalid year or month'}), 400

    user_id, err = extensions.require_login()
    if err:
        return err

    try:
        data = database.get_data_completeness_for_month(year, month)
        return jsonify({'year': year, 'month': month, 'days': data})
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/api/debug/day/<date_str>')
@extensions.limiter.limit("10 per minute")
def debug_day_data(date_str):
    """Debug endpoint to check raw hourly data for a specific day (admin only)"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    secret = request.headers.get('X-Admin-Secret') or ''
    if not extensions.ADMIN_SECRET or not secrets.compare_digest(secret, extensions.ADMIN_SECRET):
        return jsonify({'error': 'Unauthorized'}), 401

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400

    try:
        db = database.get_db()

        docs = db.collection('hourly_occupancy')\
            .where('date', '==', date_str)\
            .stream()

        hours_data = {}
        for doc in docs:
            data = doc.to_dict()
            hour = data.get('hour')
            occupancy = data.get('occupancy', 0)
            if hour is not None:
                hours_data[hour] = occupancy

        parts = date_str.split('-')
        d = dt_date(int(parts[0]), int(parts[1]), int(parts[2]))
        weekday = d.weekday()

        is_complete = database.is_complete_day(hours_data, weekday)

        if weekday in (5, 6):
            expected_range = "8-19 (weekend)"
        else:
            expected_range = "6-23 (weekday)"

        return jsonify({
            'date': date_str,
            'weekday': weekday,
            'weekday_name': ['Pon', 'Wt', 'Sr', 'Czw', 'Pt', 'Sob', 'Nd'][weekday],
            'expected_hours': expected_range,
            'hours_data': hours_data,
            'hours_collected': len(hours_data),
            'is_complete_day': is_complete
        })
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
