from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.payment_link import PaymentLink
from app.models.qr_wallet import QrWallet
from app.models.transaction import Transaction
from app.utils.security import admin_required, sanitize_string, validate_amount

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('', methods=['GET'])
@jwt_required()
@admin_required
def list_payments():
    """List all payment links (admin only)."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')

    query = PaymentLink.query.order_by(PaymentLink.created_at.desc())
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    links = [link.to_dict(include_wallet=True) for link in pagination.items]

    return jsonify({
        'payment_links': links,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@payments_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_payment():
    """Create a new payment link."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = sanitize_string(data.get('title', ''))
    description = sanitize_string(data.get('description', ''), max_length=1000)
    amount = data.get('amount')  # Can be None for "any amount"
    qr_wallet_id = data.get('qr_wallet_id')
    expires_at = data.get('expires_at')

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    if not qr_wallet_id:
        return jsonify({'error': 'QR wallet is required'}), 400

    wallet = QrWallet.query.get(qr_wallet_id)
    if not wallet or not wallet.is_active:
        return jsonify({'error': 'Invalid or inactive QR wallet'}), 400

    if amount is not None:
        if not validate_amount(amount):
            return jsonify({'error': 'Invalid amount'}), 400
        amount = float(amount)

    link = PaymentLink(
        title=title,
        description=description,
        amount=amount,
        qr_wallet_id=qr_wallet_id,
        created_by=int(get_jwt_identity()),
    )

    if expires_at:
        try:
            link.expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError:
            pass

    db.session.add(link)
    db.session.commit()

    return jsonify({
        'message': 'Payment link created',
        'payment_link': link.to_dict(include_wallet=True),
    }), 201


@payments_bp.route('/<int:link_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_payment(link_id):
    """Get payment link details (admin)."""
    link = PaymentLink.query.get_or_404(link_id)
    data = link.to_dict(include_wallet=True)
    data['transactions'] = [t.to_dict(include_proofs=True) for t in
                            link.transactions.order_by(Transaction.created_at.desc()).all()]
    return jsonify({'payment_link': data})


@payments_bp.route('/<int:link_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_payment(link_id):
    """Update a payment link."""
    link = PaymentLink.query.get_or_404(link_id)
    data = request.get_json()

    if 'title' in data:
        link.title = sanitize_string(data['title'])
    if 'description' in data:
        link.description = sanitize_string(data['description'], max_length=1000)
    if 'amount' in data:
        if data['amount'] is not None and not validate_amount(data['amount']):
            return jsonify({'error': 'Invalid amount'}), 400
        link.amount = float(data['amount']) if data['amount'] else None
    if 'status' in data and data['status'] in ['active', 'disabled']:
        link.status = data['status']
    if 'qr_wallet_id' in data:
        wallet = QrWallet.query.get(data['qr_wallet_id'])
        if wallet and wallet.is_active:
            link.qr_wallet_id = data['qr_wallet_id']
    if 'expires_at' in data:
        try:
            link.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00')) if data['expires_at'] else None
        except ValueError:
            pass

    db.session.commit()
    return jsonify({'message': 'Payment link updated', 'payment_link': link.to_dict(include_wallet=True)})


@payments_bp.route('/<int:link_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_payment(link_id):
    """Delete a payment link."""
    link = PaymentLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    return jsonify({'message': 'Payment link deleted'})


# ── PUBLIC ROUTES (no auth) ──

@payments_bp.route('/public/<slug>', methods=['GET'])
def get_public_payment(slug):
    """Get payment link details for public payment page."""
    link = PaymentLink.query.filter_by(slug=slug).first()
    if not link:
        return jsonify({'error': 'Payment link not found'}), 404

    if link.is_expired or link.status != 'active':
        return jsonify({'error': 'This payment link is no longer active', 'expired': True}), 410

    wallet = link.qr_wallet
    return jsonify({
        'payment_link': {
            'slug': link.slug,
            'title': link.title,
            'description': link.description,
            'amount': link.amount,
            'currency': link.currency,
        },
        'qr_wallet': {
            'name': wallet.name,
            'wallet_type': wallet.wallet_type,
            'qr_image_path': wallet.qr_image_path,
            'account_name': wallet.account_name,
            'account_number': wallet.account_number,
        } if wallet else None,
    })


@payments_bp.route('/public/<slug>/submit', methods=['POST'])
def submit_payment(slug):
    """Submit a payment (public - user uploads proof)."""
    link = PaymentLink.query.filter_by(slug=slug).first()
    if not link:
        return jsonify({'error': 'Payment link not found'}), 404

    if link.is_expired or link.status != 'active':
        return jsonify({'error': 'This payment link is no longer active'}), 410

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    sender_name = sanitize_string(data.get('sender_name', ''))
    amount_paid = data.get('amount_paid')
    reference_number = sanitize_string(data.get('reference_number', ''))
    sender_contact = sanitize_string(data.get('sender_contact', ''))
    notes = sanitize_string(data.get('notes', ''), max_length=500)

    if not sender_name:
        return jsonify({'error': 'Sender name is required'}), 400
    if not amount_paid or not validate_amount(amount_paid):
        return jsonify({'error': 'Valid amount is required'}), 400

    transaction = Transaction(
        payment_link_id=link.id,
        amount_paid=float(amount_paid),
        sender_name=sender_name,
        sender_contact=sender_contact,
        reference_number=reference_number,
        notes=notes,
        status='pending',
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify({
        'message': 'Payment submitted successfully. Waiting for admin approval.',
        'transaction': transaction.to_dict(),
    }), 201


# ── STATS (Admin) ──

@payments_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_stats():
    """Get dashboard statistics."""
    total_links = PaymentLink.query.count()
    active_links = PaymentLink.query.filter_by(status='active').count()
    total_transactions = Transaction.query.count()
    pending_transactions = Transaction.query.filter_by(status='pending').count()
    approved_transactions = Transaction.query.filter_by(status='approved').count()

    total_revenue = db.session.query(
        db.func.coalesce(db.func.sum(Transaction.amount_paid), 0)
    ).filter_by(status='approved').scalar()

    # Recent transactions
    recent = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()

    # Revenue by day (last 7 days)
    from datetime import timedelta
    revenue_by_day = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        day_revenue = db.session.query(
            db.func.coalesce(db.func.sum(Transaction.amount_paid), 0)
        ).filter(
            Transaction.status == 'approved',
            Transaction.created_at >= day_start,
            Transaction.created_at <= day_end,
        ).scalar()
        revenue_by_day.append({
            'date': day.isoformat(),
            'revenue': float(day_revenue),
        })

    return jsonify({
        'total_links': total_links,
        'active_links': active_links,
        'total_transactions': total_transactions,
        'pending_transactions': pending_transactions,
        'approved_transactions': approved_transactions,
        'total_revenue': float(total_revenue),
        'recent_transactions': [t.to_dict() for t in recent],
        'revenue_by_day': revenue_by_day,
    })
