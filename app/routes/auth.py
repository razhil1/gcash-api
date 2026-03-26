from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db, limiter
from app.models.user import User
from app.utils.security import validate_email, sanitize_string

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is disabled'}), 403

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'token': access_token,
        'user': user.to_dict(),
    })


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Register a new user."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = sanitize_string(data.get('name', ''))

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(email=email, name=name, role='user')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'token': access_token,
        'user': user.to_dict(),
    }), 201


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    """Get current user profile."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()})


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def change_password():
    """Change user password."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    data = request.get_json()

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'message': 'Password changed successfully'})
