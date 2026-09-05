import uuid
from datetime import datetime
from app.extensions import db


class RecoveryAction(db.Model):
    __tablename__ = 'recovery_actions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = db.Column(db.String(36), db.ForeignKey('transactions.id'), nullable=False, index=True)
    recommendation_id = db.Column(db.String(36), db.ForeignKey('recovery_recommendations.id'), nullable=True)
    action = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='PENDING')
    idempotency_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    executed_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    result = db.Column(db.Text, nullable=True)
    executed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'recommendation_id': self.recommendation_id,
            'action': self.action,
            'status': self.status,
            'idempotency_key': self.idempotency_key,
            'executed_by': self.executed_by,
            'result': self.result,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
