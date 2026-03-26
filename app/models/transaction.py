from datetime import datetime
from app.extensions import db


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    payment_link_id = db.Column(db.Integer, db.ForeignKey('payment_links.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    sender_name = db.Column(db.String(255), nullable=False)
    sender_contact = db.Column(db.String(255), default='')
    reference_number = db.Column(db.String(255), default='')
    notes = db.Column(db.Text, default='')
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_note = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    uploads = db.relationship('Upload', backref='transaction', lazy='dynamic')

    def to_dict(self, include_proofs=False):
        data = {
            'id': self.id,
            'payment_link_id': self.payment_link_id,
            'amount_paid': self.amount_paid,
            'sender_name': self.sender_name,
            'sender_contact': self.sender_contact,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'status': self.status,
            'reviewed_by': self.reviewed_by,
            'review_note': self.review_note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_proofs:
            data['proofs'] = [u.to_dict() for u in self.uploads.all()]
        return data
