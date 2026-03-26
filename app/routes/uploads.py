import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.upload import Upload
from app.models.transaction import Transaction
from app.utils.security import allowed_file

uploads_bp = Blueprint('uploads', __name__)


@uploads_bp.route('/proof/<int:transaction_id>', methods=['POST'])
def upload_proof(transaction_id):
    """Upload payment proof for a transaction (public endpoint)."""
    txn = Transaction.query.get(transaction_id)
    if not txn:
        return jsonify({'error': 'Transaction not found'}), 404

    if txn.status != 'pending':
        return jsonify({'error': 'Can only upload proof for pending transactions'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400

    # Check file size (max 3MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 3 * 1024 * 1024:
        return jsonify({'error': 'File too large. Max 3MB.'}), 400

    # Save file
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    proofs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'proofs')
    os.makedirs(proofs_dir, exist_ok=True)
    filepath = os.path.join(proofs_dir, filename)
    file.save(filepath)

    upload = Upload(
        transaction_id=transaction_id,
        file_url=f'/uploads/proofs/{filename}',
        original_filename=file.filename,
        file_size=file_size,
        status='pending',
    )
    db.session.add(upload)
    db.session.commit()

    return jsonify({
        'message': 'Proof uploaded successfully',
        'upload': upload.to_dict(),
    }), 201


@uploads_bp.route('/proof/<int:upload_id>/review', methods=['POST'])
@jwt_required()
def review_proof(upload_id):
    """Review an uploaded proof (admin)."""
    upload = Upload.query.get_or_404(upload_id)
    data = request.get_json() or {}

    action = data.get('action', '')
    if action not in ('approve', 'reject'):
        return jsonify({'error': 'Action must be approve or reject'}), 400

    from flask_jwt_extended import get_jwt_identity
    upload.status = 'approved' if action == 'approve' else 'rejected'
    upload.reviewed_by = get_jwt_identity()
    upload.review_note = data.get('note', '')
    db.session.commit()

    return jsonify({'message': f'Proof {upload.status}', 'upload': upload.to_dict()})
