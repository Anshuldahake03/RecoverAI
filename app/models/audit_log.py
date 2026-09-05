import uuid
from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_type = db.Column(db.String(50), nullable=False)
    actor_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    transaction_id = db.Column(db.String(36), db.ForeignKey('transactions.id'), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    previous_state = db.Column(db.JSON, nullable=True)
    new_state = db.Column(db.JSON, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    model_version = db.Column(db.String(50), nullable=True)
    correlation_id = db.Column(db.String(100), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'actor_type': self.actor_type,
            'actor_id': self.actor_id,
            'transaction_id': self.transaction_id,
            'event_type': self.event_type,
            'previous_state': self.previous_state,
            'new_state': self.new_state,
            'reason': self.reason,
            'model_version': self.model_version,
            'correlation_id': self.correlation_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
