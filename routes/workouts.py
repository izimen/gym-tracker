"""Workout routes: CRUD, month view, dashboard stats, strength, progression."""

from flask import Blueprint, jsonify, request, render_template, current_app
from pydantic import BaseModel, field_validator
from typing import Optional
import re
import database
from extensions import FIRESTORE_ENABLED, limiter, require_login

workouts_bp = Blueprint('workouts', __name__)


class WorkoutPayload(BaseModel):
    date: str
    body_parts: list[str]
    weight_data: Optional[dict] = None
    notes: Optional[str] = None

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Format daty musi być YYYY-MM-DD')
        return v

    @field_validator('body_parts')
    @classmethod
    def validate_body_parts(cls, v):
        if not v:
            raise ValueError('Wybierz przynajmniej jedną partię ciała')
        valid = database.BODY_PARTS.keys()
        for part in v:
            if part not in valid:
                raise ValueError(f'Nieprawidłowa partia ciała: {part}')
        return v


@workouts_bp.route('/calendar')
def calendar():
    """Serve the calendar page"""
    return render_template('calendar.html')


@workouts_bp.route('/api/workout', methods=['POST'])
@limiter.limit("60 per minute")
def save_workout():
    """Save a workout for a date"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = require_login()
    if err:
        return err

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Brak danych'}), 400

    try:
        payload = WorkoutPayload(**data)
    except Exception as e:
        return jsonify({'error': str(e).split('\n')[0]}), 400

    try:
        database.save_workout(payload.date, payload.body_parts, payload.weight_data, payload.notes, user_id)
        return jsonify({'success': True, 'date': payload.date})
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@workouts_bp.route('/api/workout/<date_str>', methods=['GET'])
@limiter.limit("60 per minute")
def get_workout(date_str):
    """Get workout for a specific date"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = require_login()
    if err:
        return err

    try:
        workout = database.get_workout(date_str, user_id)
        return jsonify(workout or {})
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@workouts_bp.route('/api/workout/<date_str>', methods=['DELETE'])
@limiter.limit("60 per minute")
def delete_workout(date_str):
    """Delete workout for a specific date"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = require_login()
    if err:
        return err

    try:
        database.delete_workout(date_str, user_id)
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@workouts_bp.route('/api/workouts/month/<int:year>/<int:month>')
@limiter.limit("30 per minute")
def get_month_workouts(year, month):
    """Get all workouts for a month"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    if not (2020 <= year <= 2100) or not (1 <= month <= 12):
        return jsonify({'error': 'Invalid year or month'}), 400

    user_id, err = require_login()
    if err:
        return err

    try:
        workouts = database.get_month_workouts(year, month, user_id)
        return jsonify({
            'year': year,
            'month': month,
            'workouts': workouts,
            'body_parts_config': database.BODY_PARTS
        })
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@workouts_bp.route('/api/workouts/dashboard')
@limiter.limit("30 per minute")
def get_workout_dashboard():
    """Get all workout stats for the dashboard"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available', 'firestore_enabled': False}), 503

    user_id, err = require_login()
    if err:
        return err

    try:
        stats = database.get_workout_dashboard_stats(user_id)
        stats['firestore_enabled'] = True
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f"Dashboard stats error: {e}")
        return jsonify({'error': 'Internal server error', 'firestore_enabled': True}), 500


@workouts_bp.route('/api/strength')
@limiter.limit("30 per minute")
def get_strength_stats():
    """Get strength statistics: PRs, volume, etc."""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    user_id, err = require_login()
    if err:
        return err

    try:
        stats = database.get_strength_stats(user_id)
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@workouts_bp.route('/api/progression/<part>')
@limiter.limit("30 per minute")
def get_progression(part):
    """Get weight progression for a specific body part"""
    if not FIRESTORE_ENABLED:
        return jsonify({'error': 'Firestore not available'}), 503

    if part not in database.BODY_PARTS:
        return jsonify({'error': f'Invalid body part: {part}'}), 400

    user_id, err = require_login()
    if err:
        return err

    try:
        progression = database.get_progression(part, user_id)
        return jsonify({
            'part': part,
            'data': progression,
            'config': database.BODY_PARTS.get(part, {})
        })
    except Exception as e:
        current_app.logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
