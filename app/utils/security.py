import re
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from app.models.user import User


from flask_jwt_extended import current_user


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user or current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_amount(amount):
    """Validate payment amount."""
    try:
        amount = float(amount)
        return amount > 0 and amount <= 1000000
    except (ValueError, TypeError):
        return False


def sanitize_string(s, max_length=255):
    """Sanitize string input."""
    if not isinstance(s, str):
        return ''
    s = s.strip()
    s = re.sub(r'<[^>]+>', '', s)  # Remove HTML tags
    return s[:max_length]


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
