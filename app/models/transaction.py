import uuid
from datetime import datetime
from app.extensions import db


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.String(36), db.ForeignKey('customers.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='FAILED', index=True)
    failure_reason = db.Column(db.String(100), nullable=True)
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    source = db.Column(db.String(100), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    predictions = db.relationship('RecoveryPrediction', backref='transaction', lazy='dynamic')
    recommendations = db.relationship('RecoveryRecommendation', backref='transaction', lazy='dynamic')
    recovery_actions = db.relationship('RecoveryAction', backref='transaction', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='transaction', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'customer_id': self.customer_id,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'status': self.status,
            'failure_reason': self.failure_reason,
            'retry_count': self.retry_count,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
