from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models.user import User
from app.models.payment_link import PaymentLink
from app.models.transaction import Transaction
from app.models.qr_wallet import QrWallet
from app.models.api_key import ApiKey
from app.utils.security import admin_required, sanitize_string

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required
def stats():
    """System-wide statistics."""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_links = PaymentLink.query.count()
    active_links = PaymentLink.query.filter_by(status='active').count()

    total_txns = Transaction.query.count()
    pending_txns = Transaction.query.filter_by(status='pending').count()
    approved_txns = Transaction.query.filter_by(status='approved').count()
    rejected_txns = Transaction.query.filter_by(status='rejected').count()

    total_revenue = db.session.query(func.sum(Transaction.amount_paid))\
        .filter_by(status='approved').scalar() or 0.0

    total_wallets = QrWallet.query.count()
    total_api_keys = ApiKey.query.filter_by(is_active=True).count()

    since_7d = datetime.utcnow() - timedelta(days=7)
    new_users_7d = User.query.filter(User.created_at >= since_7d).count()
    revenue_7d = db.session.query(func.sum(Transaction.amount_paid))\
        .filter(Transaction.status == 'approved', Transaction.created_at >= since_7d).scalar() or 0.0

    return jsonify({
        'users': {'total': total_users, 'active': active_users, 'new_7d': new_users_7d},
        'payment_links': {'total': total_links, 'active': active_links},
        'transactions': {
            'total': total_txns,
            'pending': pending_txns,
            'approved': approved_txns,
            'rejected': rejected_txns,
        },
        'revenue': {'total': round(total_revenue, 2), 'last_7_days': round(revenue_7d, 2)},
        'wallets': {'total': total_wallets},
        'api_keys': {'active': total_api_keys},
    })


@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def list_users():
    """List all users."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('q', '').strip()
    role = request.args.get('role', '')

    query = User.query.order_by(User.created_at.desc())
    if search:
        query = query.filter(
            db.or_(User.email.ilike(f'%{search}%'), User.name.ilike(f'%{search}%'))
        )
    if role:
        query = query.filter_by(role=role)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    users = []
    for u in pagination.items:
        d = u.to_dict()
        d['link_count'] = PaymentLink.query.filter_by(created_by=u.id).count()
        d['txn_count'] = 0
        d['api_key_count'] = ApiKey.query.filter_by(user_id=u.id, is_active=True).count()
        users.append(d)

    return jsonify({
        'users': users,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_user(user_id):
    """Get user details."""
    user = User.query.get_or_404(user_id)
    d = user.to_dict()
    d['payment_links'] = [lnk.to_dict() for lnk in
                          PaymentLink.query.filter_by(created_by=user_id).order_by(PaymentLink.created_at.desc()).limit(10).all()]
    d['api_key_count'] = ApiKey.query.filter_by(user_id=user_id, is_active=True).count()
    return jsonify({'user': d})


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@jwt_required()
@admin_required
def toggle_user(user_id):
    """Enable or disable a user account."""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    user.is_active = data.get('is_active', not user.is_active)
    db.session.commit()
    return jsonify({'message': f'User {"enabled" if user.is_active else "disabled"}', 'user': user.to_dict()})


@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@jwt_required()
@admin_required
def update_role(user_id):
    """Change user role."""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    role = data.get('role', '')
    if role not in ('admin', 'user'):
        return jsonify({'error': 'Role must be admin or user'}), 400
    user.role = role
    db.session.commit()
    return jsonify({'message': 'Role updated', 'user': user.to_dict()})


@admin_bp.route('/transactions', methods=['GET'])
@jwt_required()
@admin_required
def list_transactions():
    """List all transactions with filters."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')
    search = request.args.get('q', '').strip()

    query = Transaction.query.order_by(Transaction.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(
            db.or_(
                Transaction.sender_name.ilike(f'%{search}%'),
                Transaction.reference_number.ilike(f'%{search}%'),
            )
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    txns = [t.to_dict(include_proofs=True) for t in pagination.items]

    return jsonify({
        'transactions': txns,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@admin_bp.route('/transactions/<int:txn_id>/review', methods=['POST'])
@jwt_required()
@admin_required
def review_transaction(txn_id):
    """Approve or reject a transaction."""
    from flask_jwt_extended import get_jwt_identity
    txn = Transaction.query.get_or_404(txn_id)
    data = request.get_json() or {}
    action = data.get('action', '')
    if action not in ('approve', 'reject'):
        return jsonify({'error': 'Action must be approve or reject'}), 400
    txn.status = 'approved' if action == 'approve' else 'rejected'
    txn.reviewed_by = int(get_jwt_identity())
    txn.review_note = sanitize_string(data.get('note', ''), max_length=500)
    db.session.commit()
    return jsonify({'message': f'Transaction {txn.status}', 'transaction': txn.to_dict()})


@admin_bp.route('/revenue/chart', methods=['GET'])
@jwt_required()
@admin_required
def revenue_chart():
    """Revenue data for the last N days."""
    days = request.args.get('days', 7, type=int)
    data = []
    for i in range(days - 1, -1, -1):
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        rev = db.session.query(func.sum(Transaction.amount_paid))\
            .filter(Transaction.status == 'approved',
                    Transaction.created_at >= day_start,
                    Transaction.created_at < day_end).scalar() or 0.0
        count = Transaction.query.filter(
            Transaction.status == 'approved',
            Transaction.created_at >= day_start,
            Transaction.created_at < day_end).count()
        data.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'label': day_start.strftime('%b %d'),
            'revenue': round(rev, 2),
            'count': count,
        })
    return jsonify({'chart': data})


@admin_bp.route('/payment-links', methods=['GET'])
@jwt_required()
@admin_required
def list_payment_links():
    """Admin: list all payment links."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')
    search = request.args.get('q', '').strip()

    query = PaymentLink.query.order_by(PaymentLink.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(PaymentLink.title.ilike(f'%{search}%'))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    links = [l.to_dict(include_wallet=True) for l in pagination.items]
    return jsonify({'payment_links': links, 'total': pagination.total, 'pages': pagination.pages, 'current_page': page})
