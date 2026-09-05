from flask import Blueprint, jsonify
from flask_login import login_required
from app.services.ledger_service import HashChainedLedger
from app.services.predunning_service import PredunningDetector

ledger_bp = Blueprint('ledger', __name__)


@ledger_bp.route('/verify', methods=['GET'])
@login_required
def verify_chain():
    result = HashChainedLedger.verify_chain()
    return jsonify({'success': True, **result})


@ledger_bp.route('/entries', methods=['GET'])
@login_required
def list_entries():
    entries = HashChainedLedger.get_entries(limit=100)
    return jsonify({
        'success': True,
        'entries': [e.to_dict() for e in entries],
        'total': len(entries)
    })


@ledger_bp.route('/predunning', methods=['GET'])
@login_required
def predunning_scan():
    result = PredunningDetector.run_full_scan()
    return jsonify({'success': True, **result})
