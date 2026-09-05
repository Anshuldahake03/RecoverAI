import hashlib
import json
import logging
from datetime import datetime
from app.extensions import db

logger = logging.getLogger(__name__)


class HashChainedLedger:
    SHA256_HEX = 64

    @staticmethod
    def _compute_hash(sequence_number, payload, previous_hash):
        canonical = json.dumps({
            'seq': sequence_number,
            'payload': payload,
            'prev': previous_hash
        }, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    @staticmethod
    def append_entry(event_type, payload, actor_type='SYSTEM', actor_id=None,
                     transaction_id=None, correlation_id=None):
        last_entry = db.session.query(HashChainEntry).order_by(
            HashChainEntry.sequence_number.desc()
        ).first()

        seq = (last_entry.sequence_number + 1) if last_entry else 1
        prev_hash = last_entry.hash_value if last_entry else '0' * 64

        entry_hash = HashChainedLedger._compute_hash(seq, payload, prev_hash)

        entry = HashChainEntry(
            sequence_number=seq,
            event_type=event_type,
            payload=payload,
            actor_type=actor_type,
            actor_id=actor_id,
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            previous_hash=prev_hash,
            hash_value=entry_hash,
            created_at=datetime.utcnow()
        )
        db.session.add(entry)
        db.session.commit()
        logger.info(f"Ledger entry #{seq}: {event_type} hash={entry_hash[:16]}...")
        return entry

    @staticmethod
    def verify_chain():
        entries = db.session.query(HashChainEntry).order_by(
            HashChainEntry.sequence_number.asc()
        ).all()

        if not entries:
            return {'valid': True, 'entries': 0, 'broken_at': None}

        prev_expected = '0' * 64
        for entry in entries:
            computed = HashChainedLedger._compute_hash(
                entry.sequence_number, entry.payload, prev_expected
            )
            if computed != entry.hash_value:
                return {
                    'valid': False,
                    'entries': len(entries),
                    'broken_at': entry.sequence_number,
                    'expected': computed,
                    'actual': entry.hash_value
                }
            prev_expected = entry.hash_value

        return {'valid': True, 'entries': len(entries), 'broken_at': None}

    @staticmethod
    def get_entries(event_type=None, transaction_id=None, limit=100):
        query = db.session.query(HashChainEntry)
        if event_type:
            query = query.filter_by(event_type=event_type)
        if transaction_id:
            query = query.filter_by(transaction_id=transaction_id)
        return query.order_by(HashChainEntry.sequence_number.desc()).limit(limit).all()


class HashChainEntry(db.Model):
    __tablename__ = 'hash_chain_entries'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sequence_number = db.Column(db.Integer, unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    actor_type = db.Column(db.String(50), nullable=False)
    actor_id = db.Column(db.String(36), nullable=True)
    transaction_id = db.Column(db.String(36), nullable=True)
    correlation_id = db.Column(db.String(100), nullable=True)
    previous_hash = db.Column(db.String(64), nullable=False)
    hash_value = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    def to_dict(self):
        return {
            'sequence_number': self.sequence_number,
            'event_type': self.event_type,
            'payload': self.payload,
            'actor_type': self.actor_type,
            'actor_id': self.actor_id,
            'transaction_id': self.transaction_id,
            'correlation_id': self.correlation_id,
            'previous_hash': self.previous_hash,
            'hash_value': self.hash_value,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
