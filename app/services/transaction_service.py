import logging
from app.extensions import db
from app.models.transaction import Transaction
from app.models.customer import Customer
from sqlalchemy import or_

logger = logging.getLogger(__name__)


def get_transactions(page=1, page_size=25, search=None, status=None,
                     failure_reason=None, payment_method=None, date_from=None, date_to=None,
                     amount_min=None, amount_max=None, sort='created_at', sort_order='desc', source=None):
    query = Transaction.query

    if search:
        query = query.join(Customer).filter(
            or_(
                Transaction.transaction_id.ilike(f'%{search}%'),
                Customer.external_customer_id.ilike(f'%{search}%')
            )
        )
    if source:
        query = query.filter(Transaction.source == source)
    if status:
        query = query.filter(Transaction.status == status)
    if failure_reason:
        query = query.filter(Transaction.failure_reason == failure_reason)
    if payment_method:
        query = query.filter(Transaction.payment_method == payment_method)
    if date_from:
        query = query.filter(Transaction.created_at >= date_from)
    if date_to:
        query = query.filter(Transaction.created_at <= date_to)
    if amount_min is not None:
        query = query.filter(Transaction.amount >= amount_min)
    if amount_max is not None:
        query = query.filter(Transaction.amount <= amount_max)

    sort_col = getattr(Transaction, sort, Transaction.created_at)
    if sort_order == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    total = query.count()
    page_size = min(page_size, 100)
    transactions = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [t.to_dict() for t in transactions]
    _attach_recovery_insights(items)

    return {
        'transactions': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }


def _attach_recovery_insights(items):
    from app.models.recovery_prediction import RecoveryPrediction
    from app.models.recovery_recommendation import RecoveryRecommendation
    if not items:
        return
    uuids = [it.get('id') for it in items]

    preds = RecoveryPrediction.query.filter(
        RecoveryPrediction.transaction_id.in_(uuids)
    ).order_by(RecoveryPrediction.created_at.desc()).all()
    pred_by_txn = {}
    for p in preds:
        if p.transaction_id not in pred_by_txn:
            pred_by_txn[p.transaction_id] = p.probability

    recs = RecoveryRecommendation.query.filter(
        RecoveryRecommendation.transaction_id.in_(uuids)
    ).order_by(RecoveryRecommendation.created_at.desc()).all()
    rec_by_txn = {}
    for r in recs:
        if r.transaction_id not in rec_by_txn:
            rec_by_txn[r.transaction_id] = {
                'action': r.action,
                'confidence': r.confidence,
                'requires_approval': r.requires_approval,
                'decision_source': r.decision_source
            }

    for it in items:
        it['prediction_probability'] = pred_by_txn.get(it.get('id'))
        it['recommendation'] = rec_by_txn.get(it.get('id'))


def get_transaction_by_id(transaction_id):
    return Transaction.query.filter_by(transaction_id=transaction_id).first()


def get_import_batches():
    from sqlalchemy import func

    rows = db.session.query(
        Transaction.source,
        func.count(Transaction.id),
        func.sum(Transaction.amount),
        func.sum(db.case((Transaction.status == 'RECOVERED', 1), else_=0)),
        func.sum(db.case((Transaction.status == 'RECOVERED', Transaction.amount), else_=0)),
        func.sum(db.case((Transaction.status.in_(['FAILED', 'PENDING']), 1), else_=0)),
        func.max(Transaction.created_at)
    ).group_by(Transaction.source).order_by(func.max(Transaction.created_at).asc()).all()

    batches = []
    for source, count, amount, recovered, recovered_amount, at_risk, last in rows:
        batches.append({
            'source': source or 'Unlabelled',
            'transaction_count': count,
            'total_amount': round(amount or 0, 2),
            'recovered_count': recovered or 0,
            'recovered_amount': round(recovered_amount or 0, 2),
            'at_risk_count': at_risk or 0,
            'last_uploaded_at': last.isoformat() if last else None,
        })
    return batches


def get_transaction_by_uuid(txn_uuid):
    return db.session.get(Transaction, txn_uuid)


def create_transaction(data, customer):
    txn = Transaction(
        transaction_id=data['transaction_id'],
        customer_id=customer.id,
        amount=data['amount'],
        currency=data.get('currency', 'INR'),
        payment_method=data['payment_method'],
        status=data.get('status', 'FAILED'),
        failure_reason=data.get('failure_reason'),
        retry_count=data.get('retry_count', 0)
    )
    db.session.add(txn)
    db.session.commit()
    return txn


def import_transactions_csv(rows, source=None):
    created = 0
    skipped = 0
    errors = []
    created_transaction_ids = []

    for i, row in enumerate(rows):
        try:
            customer_ext_id = row.get('customer_id')
            if not customer_ext_id:
                errors.append(f'Row {i}: missing customer_id')
                skipped += 1
                continue

            customer = Customer.query.filter_by(external_customer_id=customer_ext_id).first()
            if not customer:
                customer = Customer(
                    external_customer_id=customer_ext_id,
                    successful_count=int(row.get('previous_success_count', 0)),
                    failed_count=int(row.get('previous_failure_count', 0)),
                    success_rate=float(row.get('historical_success_rate', 0)),
                    account_age_days=int(row.get('account_age_days', 30))
                )
                db.session.add(customer)
                db.session.flush()

            txn_id = row.get('transaction_id', f'TXN-{created + skipped + 1}')
            existing = Transaction.query.filter_by(transaction_id=txn_id).first()
            if existing:
                skipped += 1
                continue

            amount = float(row.get('amount', 0))
            if amount <= 0:
                errors.append(f'Row {i}: invalid amount')
                skipped += 1
                continue

            txn = Transaction(
                transaction_id=txn_id,
                customer_id=customer.id,
                amount=amount,
                currency=row.get('currency', 'INR'),
                payment_method=row.get('payment_method', 'upi'),
                status=row.get('status', 'FAILED'),
                failure_reason=row.get('failure_reason'),
                retry_count=int(row.get('retry_count', 0)),
                source=source
            )
            db.session.add(txn)
            db.session.flush()
            created += 1
            created_transaction_ids.append(txn.id)
        except Exception as e:
            errors.append(f'Row {i}: {str(e)}')
            skipped += 1

    db.session.commit()
    return {
        'created': created, 'skipped': skipped, 'errors': errors,
        'created_transaction_ids': created_transaction_ids
    }
