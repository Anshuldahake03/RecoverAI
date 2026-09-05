import random
from datetime import datetime, timedelta

from app.extensions import db
from app.models.user import User
from app.models.customer import Customer
from app.models.transaction import Transaction

SEED_SOURCE = 'Seed data (500)'


def seed_data_if_empty():
    """Create demo users and data on an empty database. Idempotent: never
    touches an existing database (skips if users already exist)."""
    created_any = False

    if not User.query.first():
        admin = User(email='admin@recoverai.com', role='MERCHANT_ADMIN')
        admin.set_password('admin123')
        db.session.add(admin)

        reviewer = User(email='reviewer@recoverai.com', role='REVIEWER')
        reviewer.set_password('reviewer123')
        db.session.add(reviewer)
        db.session.commit()
        created_any = True

    if not Customer.query.first():
        random.seed(42)
        customers = []
        for i in range(50):
            success_count = random.randint(0, 30)
            fail_count = random.randint(0, 10)
            total = success_count + fail_count
            rate = success_count / total if total > 0 else 0
            c = Customer(
                external_customer_id=f'CUST-{1000+i}',
                successful_count=success_count,
                failed_count=fail_count,
                success_rate=round(rate, 4),
                account_age_days=random.randint(10, 1500)
            )
            db.session.add(c)
            customers.append(c)

        db.session.flush()

        failure_reasons = ['temporary_failure', 'insufficient_funds', 'card_expired',
                           'authentication_failed', 'technical_error', 'bank_declined']
        methods = ['upi', 'card', 'netbanking', 'wallet']

        txn_count = 0
        for i in range(500):
            customer = random.choice(customers)
            txn = Transaction(
                transaction_id=f'TXN-{20000+i}',
                customer_id=customer.id,
                amount=round(random.uniform(100, 25000), 2),
                payment_method=random.choice(methods),
                status=random.choice(['FAILED', 'FAILED', 'FAILED', 'PENDING', 'RECOVERED']),
                failure_reason=random.choice(failure_reasons),
                retry_count=random.randint(0, 3),
                source=SEED_SOURCE,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 60))
            )
            db.session.add(txn)
            txn_count += 1

        db.session.commit()
        created_any = True

    return created_any