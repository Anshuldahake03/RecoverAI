import csv
import io
import os
from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
from app.services.transaction_service import (
    get_transactions, get_transaction_by_id, create_transaction, import_transactions_csv,
    get_import_batches,
)
from app.services.prediction_service import run_prediction
from app.services.recovery_service import create_recommendation, auto_recover_rows
from app.models.customer import Customer

transactions_bp = Blueprint('transactions', __name__)

SAMPLE_CSV_COLUMNS = [
    'customer_id', 'transaction_id', 'amount', 'currency', 'payment_method',
    'status', 'failure_reason', 'retry_count', 'previous_success_count',
    'previous_failure_count', 'historical_success_rate', 'account_age_days'
]

SAMPLE_CSV_ROWS = [
    ['CUST-001', 'UPL-TXN-1001', '4500.00', 'INR', 'upi', 'FAILED', 'temporary_failure', '0', '18', '3', '0.86', '420'],
    ['CUST-002', 'UPL-TXN-1002', '12500.00', 'INR', 'card', 'FAILED', 'technical_error', '0', '24', '6', '0.80', '780'],
    ['CUST-003', 'UPL-TXN-1003', '780.00', 'INR', 'wallet', 'FAILED', 'insufficient_funds', '0', '5', '8', '0.38', '95'],
    ['CUST-004', 'UPL-TXN-1004', '2200.00', 'INR', 'netbanking', 'FAILED', 'authentication_failed', '0', '11', '2', '0.85', '150'],
    ['CUST-005', 'UPL-TXN-1005', '560.00', 'INR', 'upi', 'FAILED', 'bank_declined', '0', '3', '9', '0.25', '40'],
    ['CUST-006', 'UPL-TXN-1006', '15900.00', 'INR', 'card', 'FAILED', 'temporary_failure', '0', '22', '4', '0.85', '610'],
    ['CUST-007', 'UPL-TXN-1007', '1990.00', 'INR', 'upi', 'FAILED', 'technical_error', '1', '9', '3', '0.75', '300'],
    ['CUST-008', 'UPL-TXN-1008', '310.00', 'INR', 'wallet', 'FAILED', 'card_expired', '0', '1', '4', '0.20', '25'],
    ['CUST-009', 'UPL-TXN-1009', '7300.00', 'INR', 'netbanking', 'FAILED', 'temporary_failure', '0', '15', '5', '0.75', '210'],
    ['CUST-010', 'UPL-TXN-1010', '900.00', 'INR', 'upi', 'FAILED', 'authentication_failed', '0', '7', '1', '0.88', '900'],
    ['CUST-010', 'UPL-TXN-1011', '23400.00', 'INR', 'emi', 'FAILED', 'temporary_failure', '0', '19', '2', '0.90', '720'],
    ['CUST-011', 'UPL-TXN-1012', '4600.00', 'INR', 'upi', 'FAILED', 'insufficient_funds', '1', '6', '6', '0.50', '85'],
    ['CUST-012', 'UPL-TXN-1013', '1200.00', 'INR', 'card', 'FAILED', 'technical_error', '0', '4', '2', '0.67', '60'],
    ['CUST-013', 'UPL-TXN-1014', '800.00', 'INR', 'upi', 'FAILED', 'bank_declined', '0', '2', '5', '0.29', '35'],
    ['CUST-014', 'UPL-TXN-1015', '5600.00', 'INR', 'netbanking', 'FAILED', 'temporary_failure', '0', '16', '4', '0.80', '350'],
]


@transactions_bp.route('/sample-csv', methods=['GET'])
@login_required
def sample_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(SAMPLE_CSV_COLUMNS)
    for row in SAMPLE_CSV_ROWS:
        writer.writerow(row)
    csv_data = buf.getvalue()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=recoverai_sample_transactions.csv'
        }
    )


@transactions_bp.route('/auto-recover', methods=['POST'])
@login_required
def auto_recover():
    if current_user.role != 'MERCHANT_ADMIN':
        return jsonify({'success': False, 'error': {
            'code': 'FORBIDDEN', 'message': 'Admin access required', 'details': {}
        }}), 403

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': 'No file uploaded', 'details': {}
        }}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': 'Only CSV files allowed', 'details': {}
        }}), 400

    if file.content_length and file.content_length > 10 * 1024 * 1024:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': 'File too large (max 10MB)', 'details': {}
        }}), 400

    source = (request.form.get('source') or '').strip()
    if not source and file.filename:
        source = os.path.splitext(file.filename)[0][:100]

    try:
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return jsonify({'success': False, 'error': {
                'code': 'VALIDATION_ERROR', 'message': 'CSV file is empty', 'details': {}
            }}), 400
        report = auto_recover_rows(rows, current_user.id, source=source)
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': f'CSV parse error: {str(e)}', 'details': {}
        }}), 400


@transactions_bp.route('', methods=['GET'])
@login_required
def list_transactions():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 25, type=int)
    search = request.args.get('search')
    status = request.args.get('status')
    failure_reason = request.args.get('failure_reason')
    payment_method = request.args.get('payment_method')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    amount_min = request.args.get('amount_min', type=float)
    amount_max = request.args.get('amount_max', type=float)
    sort = request.args.get('sort', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    source = request.args.get('source')

    from datetime import datetime
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None

    result = get_transactions(
        page=page, page_size=page_size, search=search, status=status,
        failure_reason=failure_reason, payment_method=payment_method,
        date_from=df, date_to=dt,
        amount_min=amount_min, amount_max=amount_max, sort=sort, sort_order=sort_order,
        source=source
    )
    return jsonify({'success': True, **result})


@transactions_bp.route('/import-batches', methods=['GET'])
@login_required
def import_batches():
    return jsonify({'success': True, 'batches': get_import_batches()})


@transactions_bp.route('/<transaction_id>', methods=['GET'])
@login_required
def get_transaction(transaction_id):
    txn = get_transaction_by_id(transaction_id)
    if not txn:
        return jsonify({'success': False, 'error': {
            'code': 'NOT_FOUND', 'message': 'Transaction not found', 'details': {}
        }}), 404

    data = txn.to_dict()
    data['customer'] = txn.customer.to_dict() if txn.customer else None
    return jsonify({'success': True, 'transaction': data})


@transactions_bp.route('/import', methods=['POST'])
@login_required
def import_csv():
    if current_user.role != 'MERCHANT_ADMIN':
        return jsonify({'success': False, 'error': {
            'code': 'FORBIDDEN', 'message': 'Admin access required', 'details': {}
        }}), 403

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': 'No file uploaded', 'details': {}
        }}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': 'Only CSV files allowed', 'details': {}
        }}), 400

    if file.content_length and file.content_length > 10 * 1024 * 1024:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': 'File too large (max 10MB)', 'details': {}
        }}), 400

    try:
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        result = import_transactions_csv(rows)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': {
            'code': 'VALIDATION_ERROR', 'message': f'CSV parse error: {str(e)}', 'details': {}
        }}), 400


@transactions_bp.route('/<transaction_id>/analyze', methods=['POST'])
@login_required
def analyze_transaction(transaction_id):
    from app.models.transaction import Transaction
    txn = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not txn:
        return jsonify({'success': False, 'error': {
            'code': 'NOT_FOUND', 'message': 'Transaction not found', 'details': {}
        }}), 404

    prediction = run_prediction(transaction_id)
    rec, error = create_recommendation(transaction_id, use_ai=True)

    if rec is None and error == 'Transaction already recovered':
        return jsonify({
            'success': True,
            'prediction': prediction.to_dict() if prediction else None,
            'recommendation': None,
            'notice': 'Transaction already recovered — prediction refreshed, no new recommendation'
        })

    return jsonify({
        'success': True,
        'prediction': prediction.to_dict() if prediction else None,
        'recommendation': rec.to_dict() if rec else None,
        'notice': error
    })
