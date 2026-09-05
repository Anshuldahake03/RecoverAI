from flask import Blueprint, jsonify
from flask_login import login_required
from app.services.prediction_service import get_prediction, run_prediction

predictions_bp = Blueprint('predictions', __name__)


@predictions_bp.route('/<transaction_id>', methods=['POST'])
@login_required
def create_prediction(transaction_id):
    prediction = run_prediction(transaction_id)
    if not prediction:
        return jsonify({'success': False, 'error': {
            'code': 'NOT_FOUND', 'message': 'Transaction not found', 'details': {}
        }}), 404
    return jsonify({'success': True, 'prediction': prediction.to_dict()})


@predictions_bp.route('/<transaction_id>', methods=['GET'])
@login_required
def get_prediction_detail(transaction_id):
    prediction = get_prediction(transaction_id)
    if not prediction:
        return jsonify({'success': False, 'error': {
            'code': 'NOT_FOUND', 'message': 'No prediction found', 'details': {}
        }}), 404
    return jsonify({'success': True, 'prediction': prediction.to_dict()})
