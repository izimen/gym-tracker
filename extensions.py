"""Shared Flask extensions and config — avoids circular imports between app.py and blueprints."""

from flask import session, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# These get set by app.py during initialization
FIRESTORE_ENABLED = False
ADMIN_SECRET = None
limiter = Limiter(get_remote_address, default_limits=["1000 per day", "150 per hour"], storage_uri="memory://")


def get_current_user_id():
    """Get user_id from server-side session. Returns None if not logged in."""
    return session.get('user_id')


def require_login():
    """Return (user_id, None) if logged in, or (None, error_response) if not."""
    uid = get_current_user_id()
    if uid:
        return uid, None
    return None, (jsonify({'error': 'Not authenticated'}), 401)
