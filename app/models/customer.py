import uuid
from datetime import datetime
from app.extensions import db


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_customer_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    successful_count = db.Column(db.Integer, default=0, nullable=False)
    failed_count = db.Column(db.Integer, default=0, nullable=False)
    success_rate = db.Column(db.Float, default=0.0)
    account_age_days = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    transactions = db.relationship('Transaction', backref='customer', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'external_customer_id': self.external_customer_id,
            'successful_count': self.successful_count,
            'failed_count': self.failed_count,
            'success_rate': self.success_rate,
            'account_age_days': self.account_age_days,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
