import uuid
import logging
from app.models.audit_log import AuditLog
from app.extensions import db

logger = logging.getLogger(__name__)


def log_event(event_type, actor_type='SYSTEM', actor_id=None, transaction_id=None,
              previous_state=None, new_state=None, reason=None, model_version=None,
              correlation_id=None):
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        transaction_id=transaction_id,
        event_type=event_type,
        previous_state=previous_state,
        new_state=new_state,
        reason=reason,
        model_version=model_version,
        correlation_id=correlation_id or str(uuid.uuid4())
    )
    db.session.add(entry)
    db.session.commit()
    logger.info(f"Audit: {event_type} actor={actor_type}:{actor_id} txn={transaction_id}")
    return entry


def get_audit_logs(transaction_id=None, event_type=None, actor_type=None,
                   date_from=None, date_to=None, page=1, page_size=25):
    query = AuditLog.query

    if transaction_id:
        query = query.filter_by(transaction_id=transaction_id)
    if event_type:
        query = query.filter_by(event_type=event_type)
    if actor_type:
        query = query.filter_by(actor_type=actor_type)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()

    return {
        'logs': [l.to_dict() for l in logs],
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }
