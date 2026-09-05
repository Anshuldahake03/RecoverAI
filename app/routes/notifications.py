from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.notification_service import get_notifications, mark_read, mark_all_read

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('', methods=['GET'])
@login_required
def list_notifications():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 25, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    result = get_notifications(current_user.id, unread_only=unread_only,
                               page=page, page_size=page_size)
    return jsonify({'success': True, **result})


@notifications_bp.route('/<notification_id>/read', methods=['PATCH'])
@login_required
def mark_notification_read(notification_id):
    notif = mark_read(notification_id, current_user.id)
    if not notif:
        return jsonify({'success': False, 'error': {
            'code': 'NOT_FOUND', 'message': 'Notification not found', 'details': {}
        }}), 404
    return jsonify({'success': True, 'notification': notif.to_dict()})


@notifications_bp.route('/read-all', methods=['PATCH'])
@login_required
def mark_all_notifications_read():
    mark_all_read(current_user.id)
    return jsonify({'success': True, 'message': 'All notifications marked as read'})
