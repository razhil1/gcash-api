import uuid
from datetime import datetime
from app.extensions import db


class PaymentLink(db.Model):
    __tablename__ = 'payment_links'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default='')
    amount = db.Column(db.Float, nullable=True)  # NULL = any amount
    currency = db.Column(db.String(10), default='PHP')
    status = db.Column(db.String(50), default='active')  # active, expired, disabled
    expires_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    qr_wallet_id = db.Column(db.Integer, db.ForeignKey('qr_wallets.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = db.relationship('Transaction', backref='payment_link', lazy='dynamic')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.slug:
            self.slug = uuid.uuid4().hex[:12]

    @property
    def is_expired(self):
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False

    @property
    def total_paid(self):
        return sum(t.amount_paid for t in self.transactions.filter_by(status='approved').all())

    @property
    def paid_count(self):
        return self.transactions.filter_by(status='approved').count()

    def to_dict(self, include_wallet=False):
        data = {
            'id': self.id,
            'slug': self.slug,
            'title': self.title,
            'description': self.description,
            'amount': self.amount,
            'currency': self.currency,
            'status': 'expired' if self.is_expired else self.status,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_by': self.created_by,
            'qr_wallet_id': self.qr_wallet_id,
            'total_paid': self.total_paid,
            'paid_count': self.paid_count,
            'transaction_count': self.transactions.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_wallet and self.qr_wallet:
            data['qr_wallet'] = self.qr_wallet.to_dict()
        return data
