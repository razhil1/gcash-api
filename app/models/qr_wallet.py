from datetime import datetime
from app.extensions import db


class QrWallet(db.Model):
    __tablename__ = 'qr_wallets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # "GCash", "Maya"
    wallet_type = db.Column(db.String(50), default='gcash')  # gcash, maya
    qr_image_path = db.Column(db.String(500), nullable=False)
    account_name = db.Column(db.String(255), default='')
    account_number = db.Column(db.String(50), default='')
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    payment_links = db.relationship('PaymentLink', backref='qr_wallet', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'wallet_type': self.wallet_type,
            'qr_image_path': self.qr_image_path,
            'account_name': self.account_name,
            'account_number': self.account_number,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
