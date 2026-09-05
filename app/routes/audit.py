from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.audit_service import get_audit_logs

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('', methods=['GET'])
@login_required
def list_audit_logs():
    if current_user.role != 'MERCHANT_ADMIN':
        return jsonify({'success': False, 'error': {
            'code': 'FORBIDDEN', 'message': 'Admin access required', 'details': {}
        }}), 403

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 25, type=int)
    transaction_id = request.args.get('transaction_id')
    event_type = request.args.get('event_type')
    actor_type = request.args.get('actor_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    from datetime import datetime
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None

    result = get_audit_logs(
        transaction_id=transaction_id, event_type=event_type,
        actor_type=actor_type, date_from=df, date_to=dt,
        page=page, page_size=page_size
    )
    return jsonify({'success': True, **result})
