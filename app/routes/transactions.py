from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.transaction import Transaction
from app.models.payment_link import PaymentLink
from app.utils.security import admin_required, sanitize_string

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('', methods=['GET'])
@jwt_required()
@admin_required
def list_transactions():
    """List all transactions with filters."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')
    link_id = request.args.get('link_id', type=int)

    query = Transaction.query.order_by(Transaction.created_at.desc())

    if status:
        query = query.filter_by(status=status)
    if link_id:
        query = query.filter_by(payment_link_id=link_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = []
    for t in pagination.items:
        td = t.to_dict(include_proofs=True)
        # Include payment link title
        link = PaymentLink.query.get(t.payment_link_id)
        td['payment_link_title'] = link.title if link else 'Unknown'
        td['payment_link_slug'] = link.slug if link else ''
        transactions.append(td)

    return jsonify({
        'transactions': transactions,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@transactions_bp.route('/<int:txn_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_transaction(txn_id):
    """Get transaction details."""
    txn = Transaction.query.get_or_404(txn_id)
    data = txn.to_dict(include_proofs=True)
    link = PaymentLink.query.get(txn.payment_link_id)
    data['payment_link_title'] = link.title if link else 'Unknown'
    return jsonify({'transaction': data})


@transactions_bp.route('/<int:txn_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_transaction(txn_id):
    """Approve a pending transaction."""
    txn = Transaction.query.get_or_404(txn_id)
    if txn.status != 'pending':
        return jsonify({'error': f'Transaction is already {txn.status}'}), 400

    data = request.get_json() or {}
    txn.status = 'approved'
    txn.reviewed_by = int(get_jwt_identity())
    txn.review_note = sanitize_string(data.get('note', ''), max_length=500)
    db.session.commit()

    return jsonify({'message': 'Transaction approved', 'transaction': txn.to_dict()})


@transactions_bp.route('/<int:txn_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_transaction(txn_id):
    """Reject a pending transaction."""
    txn = Transaction.query.get_or_404(txn_id)
    if txn.status != 'pending':
        return jsonify({'error': f'Transaction is already {txn.status}'}), 400

    data = request.get_json() or {}
    txn.status = 'rejected'
    txn.reviewed_by = int(get_jwt_identity())
    txn.review_note = sanitize_string(data.get('note', ''), max_length=500)
    db.session.commit()

    return jsonify({'message': 'Transaction rejected', 'transaction': txn.to_dict()})
