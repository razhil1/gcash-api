"""User-specific routes (non-admin)."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models.user import User
from app.models.payment_link import PaymentLink
from app.models.transaction import Transaction
from app.models.qr_wallet import QrWallet
from app.utils.security import sanitize_string, validate_amount

user_bp = Blueprint('user', __name__)


@user_bp.route('/stats', methods=['GET'])
@jwt_required()
def stats():
    """Stats for the current user."""
    user_id = int(get_jwt_identity())

    total_links = PaymentLink.query.filter_by(created_by=user_id).count()
    active_links = PaymentLink.query.filter_by(created_by=user_id, status='active').count()

    link_ids = [l.id for l in PaymentLink.query.filter_by(created_by=user_id).all()]
    txn_query = Transaction.query.filter(Transaction.payment_link_id.in_(link_ids)) if link_ids else Transaction.query.filter_by(id=0)

    total_txns = txn_query.count()
    pending_txns = txn_query.filter_by(status='pending').count() if link_ids else 0
    approved_txns = txn_query.filter_by(status='approved').count() if link_ids else 0

    total_revenue = db.session.query(func.sum(Transaction.amount_paid))\
        .filter(Transaction.payment_link_id.in_(link_ids), Transaction.status == 'approved').scalar() or 0.0 if link_ids else 0.0

    since_7d = datetime.utcnow() - timedelta(days=7)
    revenue_7d = db.session.query(func.sum(Transaction.amount_paid))\
        .filter(Transaction.payment_link_id.in_(link_ids),
                Transaction.status == 'approved',
                Transaction.created_at >= since_7d).scalar() or 0.0 if link_ids else 0.0

    # Revenue chart (last 7 days)
    revenue_by_day = []
    for i in range(6, -1, -1):
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        if link_ids:
            rev = db.session.query(func.sum(Transaction.amount_paid))\
                .filter(Transaction.status == 'approved',
                        Transaction.payment_link_id.in_(link_ids),
                        Transaction.created_at >= day_start,
                        Transaction.created_at < day_end).scalar() or 0.0
        else:
            rev = 0.0
        revenue_by_day.append({'date': day_start.strftime('%Y-%m-%d'), 'revenue': round(rev, 2)})

    return jsonify({
        'payment_links': {'total': total_links, 'active': active_links},
        'transactions': {'total': total_txns, 'pending': pending_txns, 'approved': approved_txns},
        'revenue': {'total': round(total_revenue, 2), 'last_7_days': round(revenue_7d, 2)},
        'revenue_by_day': revenue_by_day,
        # Legacy flat keys for dashboard compatibility
        'total_revenue': round(total_revenue, 2),
        'approved_transactions': approved_txns,
        'pending_transactions': pending_txns,
        'active_links': active_links,
    })


@user_bp.route('/transactions', methods=['GET'])
@jwt_required()
def my_transactions():
    """Transactions for links owned by the current user."""
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')

    link_ids = [l.id for l in PaymentLink.query.filter_by(created_by=user_id).all()]
    if not link_ids:
        return jsonify({'transactions': [], 'total': 0, 'pages': 0, 'current_page': 1})

    query = Transaction.query.filter(Transaction.payment_link_id.in_(link_ids))\
        .order_by(Transaction.created_at.desc())
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'transactions': [t.to_dict(include_proofs=True) for t in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@user_bp.route('/payment-links', methods=['GET'])
@jwt_required()
def my_links():
    """Payment links owned by the current user."""
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')

    query = PaymentLink.query.filter_by(created_by=user_id).order_by(PaymentLink.created_at.desc())
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'payment_links': [l.to_dict(include_wallet=True) for l in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@user_bp.route('/payment-links', methods=['POST'])
@jwt_required()
def create_link():
    """Create a payment link (user)."""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = sanitize_string(data.get('title', ''))
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    description = sanitize_string(data.get('description', ''), max_length=1000)
    amount = data.get('amount')
    qr_wallet_id = data.get('qr_wallet_id')

    if amount is not None:
        if not validate_amount(amount):
            return jsonify({'error': 'Invalid amount'}), 400
        amount = float(amount)

    if qr_wallet_id:
        wallet = QrWallet.query.filter_by(id=qr_wallet_id, created_by=user_id, is_active=True).first()
        if not wallet:
            return jsonify({'error': 'Invalid or inactive QR wallet'}), 400
    else:
        wallet = QrWallet.query.filter_by(created_by=user_id, is_active=True).first()
        if not wallet:
            return jsonify({'error': 'Create a QR wallet first'}), 400

    link = PaymentLink(
        title=title,
        description=description,
        amount=amount,
        qr_wallet_id=wallet.id,
        created_by=user_id,
    )

    expires_at = data.get('expires_at')
    if expires_at:
        try:
            link.expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError:
            pass

    db.session.add(link)
    db.session.commit()
    base_url = request.host_url.rstrip('/')
    d = link.to_dict(include_wallet=True)
    d['payment_url'] = f'{base_url}/pay/{link.slug}'
    return jsonify({'message': 'Payment link created', 'payment_link': d}), 201


@user_bp.route('/payment-links/<int:link_id>', methods=['PUT'])
@jwt_required()
def update_link(link_id):
    """Update a payment link (owner only)."""
    user_id = int(get_jwt_identity())
    link = PaymentLink.query.filter_by(id=link_id, created_by=user_id).first_or_404()
    data = request.get_json() or {}

    if 'title' in data:
        link.title = sanitize_string(data['title'])
    if 'description' in data:
        link.description = sanitize_string(data['description'], max_length=1000)
    if 'amount' in data:
        if data['amount'] is not None and not validate_amount(data['amount']):
            return jsonify({'error': 'Invalid amount'}), 400
        link.amount = float(data['amount']) if data['amount'] else None
    if 'status' in data and data['status'] in ('active', 'disabled'):
        link.status = data['status']

    db.session.commit()
    return jsonify({'message': 'Link updated', 'payment_link': link.to_dict(include_wallet=True)})


@user_bp.route('/payment-links/<int:link_id>', methods=['DELETE'])
@jwt_required()
def delete_link(link_id):
    """Disable a payment link (owner)."""
    user_id = int(get_jwt_identity())
    link = PaymentLink.query.filter_by(id=link_id, created_by=user_id).first_or_404()
    link.status = 'disabled'
    db.session.commit()
    return jsonify({'message': 'Payment link disabled'})


@user_bp.route('/wallets', methods=['GET'])
@jwt_required()
def my_wallets():
    """QR wallets owned by the current user."""
    user_id = int(get_jwt_identity())
    wallets = QrWallet.query.filter_by(created_by=user_id).order_by(QrWallet.created_at.desc()).all()
    return jsonify({'qr_wallets': [w.to_dict() for w in wallets]})
