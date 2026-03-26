from datetime import datetime
from app.extensions import db


class Upload(db.Model):
    __tablename__ = 'uploads'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'file_url': self.file_url,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'status': self.status,
            'reviewed_by': self.reviewed_by,
            'review_note': self.review_note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
