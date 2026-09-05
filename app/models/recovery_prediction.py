import uuid
from datetime import datetime
from app.extensions import db


class RecoveryPrediction(db.Model):
    __tablename__ = 'recovery_predictions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = db.Column(db.String(36), db.ForeignKey('transactions.id'), nullable=False, index=True)
    probability = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(50), nullable=False)
    feature_version = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'probability': self.probability,
            'model_version': self.model_version,
            'feature_version': self.feature_version,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
