import secrets
from datetime import datetime
from app.extensions import db


class ApiKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, default='My API Key')
    is_active = db.Column(db.Boolean, default=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    request_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('api_keys', lazy='dynamic'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.key:
            self.key = self._generate_key()

    @staticmethod
    def _generate_key():
        return 'qrp_' + secrets.token_urlsafe(40)

    def record_usage(self):
        self.last_used_at = datetime.utcnow()
        self.request_count = (self.request_count or 0) + 1
        db.session.commit()

    def to_dict(self, reveal_key=False):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'key': self.key if reveal_key else self.key[:12] + '...' + self.key[-4:],
            'is_active': self.is_active,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'request_count': self.request_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
