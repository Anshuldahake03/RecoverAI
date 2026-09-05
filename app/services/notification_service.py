import logging
from app.models.notification import Notification
from app.extensions import db

logger = logging.getLogger(__name__)


def create_notification(user_id, notif_type, title, message):
    notif = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        message=message
    )
    db.session.add(notif)
    db.session.commit()
    logger.info(f"Notification created: {notif_type} for user {user_id}")
    return notif


def get_notifications(user_id, unread_only=False, page=1, page_size=25):
    query = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)
    total = query.count()
    notifs = query.order_by(Notification.created_at.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()
    return {
        'notifications': [n.to_dict() for n in notifs],
        'total': total,
        'unread_count': Notification.query.filter_by(user_id=user_id, is_read=False).count(),
        'page': page,
        'page_size': page_size
    }


def mark_read(notification_id, user_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not notif:
        return None
    notif.is_read = True
    db.session.commit()
    return notif


def mark_all_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
