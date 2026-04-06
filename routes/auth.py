"""Authentication routes: register, login, logout, session check."""

from flask import Blueprint, jsonify, request, session, current_app
import database
import extensions

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/register', methods=['POST'])
@extensions.limiter.limit("5 per minute")
def register_user():
    """Register a new user"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'success': False, 'error': 'Firestore not available'}), 503

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    result = database.create_user(username, password)

    if result['success']:
        session.permanent = True
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        return jsonify(result)
    else:
        return jsonify(result), 400


@auth_bp.route('/api/auth/login', methods=['POST'])
@extensions.limiter.limit("10 per minute")
def login_user():
    """Login with username and password"""
    if not extensions.FIRESTORE_ENABLED:
        return jsonify({'success': False, 'error': 'Firestore not available'}), 503

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    result = database.authenticate_user(username, password)

    if result['success']:
        session.permanent = True
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        return jsonify(result)
    else:
        return jsonify(result), 401


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout_user():
    """Logout: clear server-side session"""
    session.clear()
    return jsonify({'success': True})


@auth_bp.route('/api/auth/me')
def auth_me():
    """Check if current session is valid. Returns user info or 401."""
    uid = extensions.get_current_user_id()
    if uid:
        return jsonify({'user_id': uid, 'username': session.get('username', '')})
    return jsonify({'error': 'Not authenticated'}), 401
