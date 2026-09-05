from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.services.audit_service import log_event

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': 'Email and password required', 'details': {}
        }}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'error': {
            'code': 'CONFLICT', 'message': 'Email already registered', 'details': {}
        }}), 409

    user = User(email=data['email'], role=data.get('role', 'MERCHANT_ADMIN'))
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    log_event(event_type='REGISTRATION', actor_type='USER', actor_id=user.id,
              new_state={'email': user.email, 'role': user.role})

    return jsonify({'success': True, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': 'Email and password required', 'details': {}
        }}), 400

    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'success': False, 'error': {
            'code': 'INVALID_CREDENTIALS', 'message': 'Invalid email or password', 'details': {}
        }}), 401

    if not user.is_active:
        return jsonify({'success': False, 'error': {
            'code': 'FORBIDDEN', 'message': 'Account is inactive', 'details': {}
        }}), 403

    login_user(user, remember=True)
    log_event(event_type='LOGIN', actor_type='USER', actor_id=user.id)

    return jsonify({'success': True, 'user': user.to_dict()})


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    log_event(event_type='LOGOUT', actor_type='USER', actor_id=current_user.id)
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify({'success': True, 'user': current_user.to_dict()})
