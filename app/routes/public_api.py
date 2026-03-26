"""
Public REST API v1 — authenticated via API key (Authorization: Bearer qrp_...)
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from app.extensions import db, limiter
from app.models.api_key import ApiKey
from app.models.payment_link import PaymentLink
from app.models.qr_wallet import QrWallet
from app.utils.security import sanitize_string, validate_amount

public_api_bp = Blueprint('public_api', __name__)


def _get_api_user():
    """Extract and validate API key from Authorization header."""
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        raw_key = auth[7:].strip()
    else:
        raw_key = request.headers.get('X-API-Key', '').strip()

    if not raw_key:
        return None, None

    api_key = ApiKey.query.filter_by(key=raw_key, is_active=True).first()
    if not api_key:
        return None, None

    api_key.record_usage()
    return api_key.user, api_key


def _api_auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user, api_key = _get_api_user()
        if not user:
            return jsonify({'error': 'Invalid or missing API key', 'code': 'UNAUTHORIZED'}), 401
        if not user.is_active:
            return jsonify({'error': 'Account disabled', 'code': 'FORBIDDEN'}), 403
        request.api_user = user
        request.api_key = api_key
        return f(*args, **kwargs)
    return decorated


@public_api_bp.route('/links', methods=['POST'])
@limiter.limit("60 per minute")
@_api_auth_required
def create_link():
    """
    Create a payment link via API.

    Body (JSON):
      title        string  required
      amount       float   optional (null = any amount)
      description  string  optional
      qr_wallet_id int     optional (defaults to user's active wallet)
      expires_at   ISO8601 optional
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    user = request.api_user
    title = sanitize_string(data.get('title', ''))
    if not title:
        return jsonify({'error': 'title is required'}), 400

    description = sanitize_string(data.get('description', ''), max_length=1000)
    amount = data.get('amount')
    if amount is not None:
        if not validate_amount(amount):
            return jsonify({'error': 'Invalid amount (must be > 0 and ≤ 1,000,000)'}), 400
        amount = float(amount)

    qr_wallet_id = data.get('qr_wallet_id')
    if qr_wallet_id:
        wallet = QrWallet.query.filter_by(id=qr_wallet_id, created_by=user.id, is_active=True).first()
        if not wallet:
            return jsonify({'error': 'Invalid or inactive QR wallet'}), 400
    else:
        wallet = QrWallet.query.filter_by(created_by=user.id, is_active=True).first()
        if not wallet:
            return jsonify({'error': 'No active QR wallet found. Create one in the dashboard first.'}), 400

    link = PaymentLink(
        title=title,
        description=description,
        amount=amount,
        qr_wallet_id=wallet.id,
        created_by=user.id,
    )

    expires_at = data.get('expires_at')
    if expires_at:
        try:
            link.expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid expires_at format. Use ISO 8601.'}), 400

    db.session.add(link)
    db.session.commit()

    base_url = request.host_url.rstrip('/')
    return jsonify({
        'id': link.id,
        'slug': link.slug,
        'title': link.title,
        'amount': link.amount,
        'currency': link.currency,
        'status': link.status,
        'payment_url': f'{base_url}/pay/{link.slug}',
        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
        'created_at': link.created_at.isoformat(),
    }), 201


@public_api_bp.route('/links', methods=['GET'])
@limiter.limit("120 per minute")
@_api_auth_required
def list_links():
    """List payment links for the authenticated user."""
    user = request.api_user
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status', '')

    query = PaymentLink.query.filter_by(created_by=user.id).order_by(PaymentLink.created_at.desc())
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    base_url = request.host_url.rstrip('/')

    links = []
    for link in pagination.items:
        d = link.to_dict()
        d['payment_url'] = f'{base_url}/pay/{link.slug}'
        links.append(d)

    return jsonify({
        'data': links,
        'meta': {
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page,
        }
    })


@public_api_bp.route('/links/<slug>', methods=['GET'])
@limiter.limit("120 per minute")
@_api_auth_required
def get_link(slug):
    """Get a specific payment link."""
    user = request.api_user
    link = PaymentLink.query.filter_by(slug=slug, created_by=user.id).first_or_404()
    base_url = request.host_url.rstrip('/')
    d = link.to_dict(include_wallet=True)
    d['payment_url'] = f'{base_url}/pay/{link.slug}'
    return jsonify({'data': d})


@public_api_bp.route('/links/<slug>', methods=['DELETE'])
@limiter.limit("30 per minute")
@_api_auth_required
def disable_link(slug):
    """Disable a payment link."""
    user = request.api_user
    link = PaymentLink.query.filter_by(slug=slug, created_by=user.id).first_or_404()
    link.status = 'disabled'
    db.session.commit()
    return jsonify({'message': 'Payment link disabled'})


@public_api_bp.route('/me', methods=['GET'])
@_api_auth_required
def get_me():
    """Get authenticated user info."""
    user = request.api_user
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
    })
