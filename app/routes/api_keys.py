from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db, limiter
from app.models.api_key import ApiKey
from app.utils.security import sanitize_string

api_keys_bp = Blueprint('api_keys', __name__)


@api_keys_bp.route('', methods=['GET'])
@jwt_required()
def list_keys():
    """List API keys for the current user."""
    user_id = int(get_jwt_identity())
    keys = ApiKey.query.filter_by(user_id=user_id).order_by(ApiKey.created_at.desc()).all()
    return jsonify({'api_keys': [k.to_dict() for k in keys]})


@api_keys_bp.route('', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def create_key():
    """Generate a new API key."""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    if ApiKey.query.filter_by(user_id=user_id, is_active=True).count() >= 10:
        return jsonify({'error': 'Maximum of 10 active API keys allowed'}), 400

    name = sanitize_string(data.get('name', 'My API Key'), max_length=100)
    key = ApiKey(user_id=user_id, name=name)
    db.session.add(key)
    db.session.commit()

    return jsonify({
        'message': 'API key created. Save this key — it will not be shown again in full.',
        'api_key': key.to_dict(reveal_key=True),
    }), 201


@api_keys_bp.route('/<int:key_id>', methods=['DELETE'])
@jwt_required()
def revoke_key(key_id):
    """Revoke an API key."""
    user_id = int(get_jwt_identity())
    key = ApiKey.query.filter_by(id=key_id, user_id=user_id).first_or_404()
    key.is_active = False
    db.session.commit()
    return jsonify({'message': 'API key revoked'})


@api_keys_bp.route('/<int:key_id>/name', methods=['PUT'])
@jwt_required()
def rename_key(key_id):
    """Rename an API key."""
    user_id = int(get_jwt_identity())
    key = ApiKey.query.filter_by(id=key_id, user_id=user_id).first_or_404()
    data = request.get_json() or {}
    name = sanitize_string(data.get('name', ''), max_length=100)
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    key.name = name
    db.session.commit()
    return jsonify({'message': 'Key renamed', 'api_key': key.to_dict()})
