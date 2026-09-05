import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    db.create_all()

    # Lightweight migration: add `source` (batch label) column if missing
    cols = [c["name"] for c in db.inspect(db.engine).get_columns("transactions")]
    if "source" not in cols:
        db.session.execute(db.text("ALTER TABLE transactions ADD COLUMN source VARCHAR(100)"))
        db.session.commit()

    # Backfill labels for existing demo + prior uploads once
    from app.models.transaction import Transaction
    backfill = {
        'TXN-': 'Seed data (500)',
        'UPL-TXN-': 'sample_transactions.csv',
        'SPL-TXN-': 'sample_transactions_2.csv',
    }
    for prefix_key, source in backfill.items():
        db.session.query(Transaction).filter(
            Transaction.transaction_id.like(prefix_key + '%'),
            Transaction.source.is_(None)
        ).update({'source': source}, synchronize_session=False)
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
