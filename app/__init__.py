import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import Config
from app.extensions import db, migrate, login_manager


def create_app(config_class=Config):
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['http://localhost:5000']),
         supports_credentials=True)

    _configure_logging(app)

    from app.routes.auth import auth_bp
    from app.routes.transactions import transactions_bp
    from app.routes.predictions import predictions_bp
    from app.routes.recovery import recovery_bp
    from app.routes.analytics import analytics_bp
    from app.routes.audit import audit_bp
    from app.routes.notifications import notifications_bp
    from app.routes.frontend import frontend_bp
    from app.routes.webhooks import webhooks_bp
    from app.routes.ledger import ledger_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(predictions_bp, url_prefix='/api/predictions')
    app.register_blueprint(recovery_bp, url_prefix='/api/recovery')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(audit_bp, url_prefix='/api/audit-logs')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(webhooks_bp, url_prefix='/api/webhooks')
    app.register_blueprint(ledger_bp, url_prefix='/api/ledger')
    app.register_blueprint(frontend_bp)

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'})

    from app.models import user, customer, transaction, recovery_prediction, \
        recovery_recommendation, recovery_action, audit_log, notification
    from app.services.ledger_service import HashChainEntry

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return db.session.get(User, user_id)

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'success': False, 'error': {
            'code': 'AUTHENTICATION_REQUIRED',
            'message': 'Authentication required',
            'details': {}
        }}), 401

    @app.context_processor
    def inject_app_globals():
        import os
        from flask import request
        endpoint = request.endpoint or ''
        nav_map = {
            'frontend.dashboard': 'dashboard',
            'frontend.transactions_page': 'transactions',
            'frontend.transaction_detail_page': 'transactions',
            'frontend.recovery_page': 'recovery',
            'frontend.analytics_page': 'analytics',
            'frontend.audit_logs_page': 'audit-logs',
            'frontend.notifications_page': 'notifications',
        }
        rz_mode = 'TEST_API' if os.environ.get('RAZORPAY_KEY_SECRET') else 'SIMULATED'
        llm_configured = bool(os.environ.get('LLM_API_KEY'))
        return {
            'active_nav': nav_map.get(endpoint, ''),
            'app_name': 'RecoverAI',
            'rz_mode': rz_mode,
            'llm_configured': llm_configured
        }

    app.register_error_handler(400, lambda e: _error_response('VALIDATION_ERROR', str(e), 400))
    app.register_error_handler(404, lambda e: _error_response('NOT_FOUND', 'Resource not found', 404))
    app.register_error_handler(409, lambda e: _error_response('CONFLICT', 'Resource conflict', 409))
    app.register_error_handler(429, lambda e: _error_response('RATE_LIMITED', 'Rate limited', 429))
    app.register_error_handler(500, lambda e: _error_response('INTERNAL_ERROR', 'Internal server error', 500))

    return app


def _error_response(code, message, status_code):
    return jsonify({'success': False, 'error': {
        'code': code, 'message': message, 'details': {}
    }}), status_code


def _configure_logging(app):
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )
