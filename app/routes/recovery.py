from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.recovery_service import (
    get_recovery_status, get_recovery_detail, create_recommendation,
    approve_recommendation, reject_recommendation, execute_recovery
)
from app.services.policy_service import validate_policy
from app.models.transaction import Transaction
from app.models.recovery_action import RecoveryAction
from app.models.recovery_recommendation import RecoveryRecommendation
from app.services.audit_service import log_event

recovery_bp = Blueprint('recovery', __name__)


@recovery_bp.route('', methods=['GET'])
@login_required
def list_recovery():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 25, type=int)
    txn_id = request.args.get('transaction_id')
    status_filter = request.args.get('status')

    result = get_recovery_status(
        transaction_id=txn_id, page=page,
        page_size=page_size, status_filter=status_filter
    )
    return jsonify({'success': True, **result})


@recovery_bp.route('/<transaction_id>', methods=['GET'])
@login_required
def detail(transaction_id):
    result = get_recovery_detail(transaction_id)
    if not result:
        return jsonify({'success': False, 'error': {
            'code': 'NOT_FOUND', 'message': 'Recovery case not found', 'details': {}
        }}), 404
    return jsonify({'success': True, **result})


@recovery_bp.route('/<transaction_id>/recommend', methods=['POST'])
@login_required
def recommend(transaction_id):
    use_ai = request.args.get('use_ai', 'true').lower() == 'true'
    rec, error = create_recommendation(transaction_id, use_ai=use_ai)

    if error:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': error, 'details': {}
        }}), 400

    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    existing_actions = RecoveryAction.query.filter_by(transaction_id=txn.id).all() if txn else []
    policy_result = validate_policy(txn, rec, existing_actions) if txn else None

    return jsonify({
        'success': True,
        'recommendation': rec.to_dict(),
        'policy': policy_result
    })


@recovery_bp.route('/<transaction_id>/approve', methods=['POST'])
@login_required
def approve(transaction_id):
    if not current_user.has_role('MERCHANT_ADMIN', 'REVIEWER'):
        return jsonify({'success': False, 'error': {
            'code': 'FORBIDDEN', 'message': 'Insufficient permissions', 'details': {}
        }}), 403

    data = request.get_json(silent=True) or {}
    reason = data.get('reason', 'Approved by admin')

    action, error = approve_recommendation(transaction_id, current_user.id, reason)
    if error:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': error, 'details': {}
        }}), 400

    return jsonify({'success': True, 'action': action.to_dict()})


@recovery_bp.route('/<transaction_id>/reject', methods=['POST'])
@login_required
def reject(transaction_id):
    if not current_user.has_role('MERCHANT_ADMIN', 'REVIEWER'):
        return jsonify({'success': False, 'error': {
            'code': 'FORBIDDEN', 'message': 'Insufficient permissions', 'details': {}
        }}), 403

    data = request.get_json(silent=True) or {}
    reason = data.get('reason', 'Rejected by admin')

    action, error = reject_recommendation(transaction_id, current_user.id, reason)
    if error:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': error, 'details': {}
        }}), 400

    return jsonify({'success': True, 'action': action.to_dict()})


@recovery_bp.route('/<transaction_id>/execute', methods=['POST'])
@login_required
def execute(transaction_id):
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return jsonify({'success': False, 'error': {
            'code': 'NOT_FOUND', 'message': 'Transaction not found', 'details': {}
        }}), 404

    existing_actions = [a for a in RecoveryAction.query.filter_by(
        transaction_id=txn.id
    ).all() if a.status not in ('APPROVED', 'COMPLETED')]
    latest_rec = RecoveryRecommendation.query.filter_by(
        transaction_id=txn.id
    ).order_by(RecoveryRecommendation.created_at.desc()).first()
    policy_result = validate_policy(txn, latest_rec, existing_actions) if latest_rec else {
        'allowed': True, 'requires_approval': True,
        'reason': 'No recommendation exists yet', 'checks': {}
    }

    if not policy_result['allowed']:
        log_event(
            event_type='POLICY_BLOCKED',
            actor_type='USER',
            actor_id=current_user.id,
            transaction_id=txn.id,
            new_state={'policy': policy_result},
            reason=policy_result['reason']
        )
        return jsonify({'success': False, 'error': {
            'code': 'POLICY_BLOCKED', 'message': policy_result['reason'],
            'details': policy_result['checks']
        }}), 403

    action, error = execute_recovery(transaction_id, current_user.id)
    if error:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': error, 'details': {}
        }}), 400

    return jsonify({'success': True, 'action': action.to_dict()})
