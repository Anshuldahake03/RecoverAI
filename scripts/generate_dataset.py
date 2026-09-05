import os
import sys
import random
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def generate_dataset(n_records=20000, seed=42):
    np.random.seed(seed)
    random.seed(seed)

    failure_reasons = ['temporary_failure', 'insufficient_funds', 'card_expired',
                       'authentication_failed', 'technical_error', 'bank_declined']
    failure_weights = [0.3, 0.25, 0.15, 0.15, 0.1, 0.05]
    methods = ['upi', 'card', 'netbanking', 'wallet', 'emi']
    method_weights = [0.35, 0.3, 0.2, 0.1, 0.05]

    records = []
    for i in range(n_records):
        amount = round(np.random.lognormal(mean=7.5, sigma=1.2), 2)
        amount = max(50, min(100000, amount))
        failure = np.random.choice(failure_reasons, p=failure_weights)
        method = np.random.choice(methods, p=method_weights)
        retry_count = np.random.choice([0, 1, 2, 3], p=[0.5, 0.25, 0.15, 0.1])
        prev_success = np.random.randint(0, 30)
        prev_failure = np.random.randint(0, 10)
        total = prev_success + prev_failure
        success_rate = prev_success / total if total > 0 else 0.5
        account_age = np.random.randint(5, 2000)

        prob = 0.5
        if success_rate >= 0.8:
            prob += 0.25
        elif success_rate >= 0.6:
            prob += 0.15
        elif success_rate < 0.3:
            prob -= 0.2
        if retry_count == 0:
            prob += 0.1
        elif retry_count >= 2:
            prob -= 0.25
        if failure == 'temporary_failure':
            prob += 0.15
        elif failure in ('card_expired', 'bank_declined'):
            prob -= 0.15
        if amount > 10000:
            prob -= 0.1
        if account_age > 365:
            prob += 0.05
        elif account_age < 30:
            prob -= 0.05

        prob += np.random.normal(0, 0.1)
        prob = max(0.05, min(0.95, prob))
        recovery_success = 1 if random.random() < prob else 0

        records.append({
            'transaction_id': f'SYN-TXN-{i:06d}',
            'customer_id': f'CUST-{random.randint(1, 500):04d}',
            'amount': amount,
            'payment_method': method,
            'failure_reason': failure,
            'retry_count': retry_count,
            'previous_success_count': prev_success,
            'previous_failure_count': prev_failure,
            'historical_success_rate': round(success_rate, 4),
            'account_age_days': account_age,
            'hour': random.randint(0, 23),
            'day_of_week': random.randint(0, 6),
            'recovery_success': recovery_success
        })

    df = pd.DataFrame(records)

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'generated')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'synthetic_dataset.csv')
    df.to_csv(output_path, index=False)
    print(f"Generated {n_records} records to {output_path}")
    print(f"Recovery success rate: {df['recovery_success'].mean():.4f}")

    return df


if __name__ == '__main__':
    generate_dataset()
