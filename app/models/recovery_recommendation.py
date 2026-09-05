import uuid
from datetime import datetime
from app.extensions import db


class RecoveryRecommendation(db.Model):
    __tablename__ = 'recovery_recommendations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = db.Column(db.String(36), db.ForeignKey('transactions.id'), nullable=False, index=True)
    action = db.Column(db.String(30), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    requires_approval = db.Column(db.Boolean, nullable=False, default=False)
    decision_source = db.Column(db.String(30), default='AI_AGENT')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    recovery_actions = db.relationship('RecoveryAction', backref='recommendation', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'action': self.action,
            'confidence': self.confidence,
            'reason': self.reason,
            'requires_approval': self.requires_approval,
            'decision_source': self.decision_source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
