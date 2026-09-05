from flask import Blueprint, jsonify
from flask_login import login_required
from app.services.analytics_service import (
    get_overview, get_recovery_analytics, get_model_metrics, get_batch_recovery_report,
    get_recovery_trend
)

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/overview', methods=['GET'])
@login_required
def overview():
    return jsonify({'success': True, 'overview': get_overview()})


@analytics_bp.route('/recovery', methods=['GET'])
@login_required
def recovery():
    return jsonify({'success': True, 'analytics': get_recovery_analytics()})


@analytics_bp.route('/model', methods=['GET'])
@login_required
def model():
    return jsonify({'success': True, 'metrics': get_model_metrics()})


@analytics_bp.route('/recovery-trend', methods=['GET'])
@login_required
def recovery_trend():
    return jsonify({'success': True, 'trend': get_recovery_trend()})


@analytics_bp.route('/batch-report', methods=['GET'])
@login_required
def batch_report():
    return jsonify({'success': True, 'report': get_batch_recovery_report()})
