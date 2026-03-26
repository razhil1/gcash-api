import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.qr_wallet import QrWallet
from app.utils.security import admin_required, allowed_file, sanitize_string

qr_wallets_bp = Blueprint('qr_wallets', __name__)


@qr_wallets_bp.route('', methods=['GET'])
@jwt_required()
@admin_required
def list_wallets():
    """List all QR wallets."""
    wallets = QrWallet.query.order_by(QrWallet.created_at.desc()).all()
    return jsonify({'qr_wallets': [w.to_dict() for w in wallets]})


@qr_wallets_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_wallet():
    """Create a new QR wallet with uploaded QR image."""
    if 'qr_image' not in request.files:
        return jsonify({'error': 'QR image is required'}), 400

    file = request.files['qr_image']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400

    name = sanitize_string(request.form.get('name', ''))
    wallet_type = request.form.get('wallet_type', 'gcash')
    account_name = sanitize_string(request.form.get('account_name', ''))
    account_number = sanitize_string(request.form.get('account_number', ''))

    if not name:
        return jsonify({'error': 'Wallet name is required'}), 400

    if wallet_type not in ('gcash', 'maya'):
        wallet_type = 'gcash'

    # Save the QR image
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qr_codes')
    os.makedirs(qr_dir, exist_ok=True)
    filepath = os.path.join(qr_dir, filename)
    file.save(filepath)

    wallet = QrWallet(
        name=name,
        wallet_type=wallet_type,
        qr_image_path=f'/uploads/qr_codes/{filename}',
        account_name=account_name,
        account_number=account_number,
        is_active=True,
        created_by=int(get_jwt_identity()),
    )
    db.session.add(wallet)
    db.session.commit()

    return jsonify({
        'message': 'QR wallet created',
        'qr_wallet': wallet.to_dict(),
    }), 201


@qr_wallets_bp.route('/<int:wallet_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_wallet(wallet_id):
    """Update QR wallet details."""
    wallet = QrWallet.query.get_or_404(wallet_id)

    # Check if there's a new QR image
    if 'qr_image' in request.files:
        file = request.files['qr_image']
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f'{uuid.uuid4().hex}.{ext}'
            qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qr_codes')
            filepath = os.path.join(qr_dir, filename)
            file.save(filepath)
            wallet.qr_image_path = f'/uploads/qr_codes/{filename}'

    # Update text fields
    if request.form.get('name'):
        wallet.name = sanitize_string(request.form['name'])
    if request.form.get('wallet_type') in ('gcash', 'maya'):
        wallet.wallet_type = request.form['wallet_type']
    if request.form.get('account_name') is not None:
        wallet.account_name = sanitize_string(request.form['account_name'])
    if request.form.get('account_number') is not None:
        wallet.account_number = sanitize_string(request.form['account_number'])
    if request.form.get('is_active') is not None:
        wallet.is_active = request.form['is_active'].lower() == 'true'

    db.session.commit()
    return jsonify({'message': 'Wallet updated', 'qr_wallet': wallet.to_dict()})


@qr_wallets_bp.route('/<int:wallet_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_wallet(wallet_id):
    """Delete a QR wallet."""
    wallet = QrWallet.query.get_or_404(wallet_id)

    # Check if wallet has payment links
    if wallet.payment_links.count() > 0:
        return jsonify({'error': 'Cannot delete wallet with active payment links. Disable it instead.'}), 400

    db.session.delete(wallet)
    db.session.commit()
    return jsonify({'message': 'Wallet deleted'})
