import os
import sys
import json
import time
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.extensions import db
from app.models.transaction import Transaction
from app.models.recovery_prediction import RecoveryPrediction
from app.models.recovery_recommendation import RecoveryRecommendation
from app.models.recovery_action import RecoveryAction
from app.ml.predict import predict_recovery_probability, MODEL_VERSION, FEATURE_VERSION
from app.ai.agent import get_ai_recommendation, get_fallback_recommendation
from app.services.policy_service import validate_policy
from app.services.audit_service import log_event
from app.services.analytics_service import get_batch_recovery_report


def run_batch_experiment(batch_size=1000):
    app = create_app()
    with app.app_context():
        print(f"\n{'='*60}")
        print(f"RecoverAI Batch Recovery Experiment")
        print(f"{'='*60}\n")

        failed_txns = Transaction.query.filter(
            Transaction.status.in_(['FAILED', 'PENDING'])
        ).limit(batch_size).all()

        if not failed_txns:
            print("No failed transactions found. Run seed.py first.")
            return

        print(f"Batch size: {len(failed_txns)}")
        print(f"Running at: {datetime.utcnow().isoformat()}\n")

        results = {
            'eligible': 0, 'predicted': 0, 'recommended': 0,
            'policy_blocked': 0, 'auto_executed': 0, 'escalated': 0,
            'recovered': 0, 'failed': 0, 'recovered_revenue': 0,
            'revenue_at_risk': 0, 'baseline_recovered': 0,
            'baseline_revenue': 0, 'latencies': []
        }

        for i, txn in enumerate(failed_txns):
            results['revenue_at_risk'] += txn.amount
            customer = txn.customer

            start = time.time()

            features = {
                'amount': txn.amount,
                'payment_method': txn.payment_method,
                'failure_reason': txn.failure_reason,
                'retry_count': txn.retry_count,
                'customer_successful_count': customer.successful_count if customer else 0,
                'customer_failed_count': customer.failed_count if customer else 0,
                'historical_success_rate': customer.success_rate if customer else 0,
                'account_age_days': customer.account_age_days if customer else 0,
            }

            probability = predict_recovery_probability(features)

            prediction = RecoveryPrediction(
                transaction_id=txn.id,
                probability=probability,
                model_version=MODEL_VERSION,
                feature_version=FEATURE_VERSION
            )
            db.session.add(prediction)
            results['predicted'] += 1

            context = {
                'transaction_id': txn.transaction_id,
                'amount': txn.amount,
                'failure_reason': txn.failure_reason,
                'retry_count': txn.retry_count,
                'previous_success_rate': customer.success_rate if customer else 0,
                'recovery_probability': probability,
                'payment_method': txn.payment_method
            }

            ai_result = get_ai_recommendation(context)
            if ai_result is None:
                ai_result = get_fallback_recommendation(context)

            action = ai_result.get('action', 'NO_ACTION')

            rec = RecoveryRecommendation(
                transaction_id=txn.id,
                action=action,
                confidence=ai_result.get('confidence', 0.5),
                reason=ai_result.get('reason', ''),
                requires_approval=ai_result.get('requires_human_approval', False),
                decision_source=ai_result.get('decision_source', 'AI_AGENT')
            )
            db.session.add(rec)
            results['recommended'] += 1

            existing_actions = RecoveryAction.query.filter_by(transaction_id=txn.id).all()
            policy_result = validate_policy(txn, rec, existing_actions)

            if not policy_result['allowed']:
                results['policy_blocked'] += 1
                continue

            results['eligible'] += 1

            if action in ('RETRY', 'SEND_PAYMENT_LINK', 'SEND_REMINDER') and not policy_result['requires_approval']:
                import random
                success = random.random() < probability

                action_record = RecoveryAction(
                    transaction_id=txn.id,
                    recommendation_id=rec.id,
                    action=action,
                    status='COMPLETED' if success else 'FAILED',
                    idempotency_key=f'batch-{txn.id}-{i}',
                    result=f'{action} batch simulation'
                )
                db.session.add(action_record)
                results['auto_executed'] += 1

                if success:
                    results['recovered'] += 1
                    results['recovered_revenue'] += txn.amount
                    txn.status = 'RECOVERED'
                else:
                    results['failed'] += 1
            elif action == 'ESCALATE':
                results['escalated'] += 1
            else:
                results['failed'] += 1

            elapsed = time.time() - start
            results['latencies'].append(elapsed)

            if (i + 1) % 100 == 0:
                print(f"  Processed {i+1}/{len(failed_txns)}...")

        db.session.commit()

        avg_latency = sum(results['latencies']) / len(results['latencies']) if results['latencies'] else 0
        recovery_rate = (results['recovered'] / results['eligible'] * 100) if results['eligible'] > 0 else 0
        revenue_recovery = (results['recovered_revenue'] / results['revenue_at_risk'] * 100) if results['revenue_at_risk'] > 0 else 0

        baseline_recoverable = sum(1 for t in failed_txns if t.retry_count == 0 and (t.customer.success_rate if t.customer else 0) >= 0.7)
        baseline_rate = (baseline_recoverable / len(failed_txns) * 100) if failed_txns else 0

        print(f"\n{'='*60}")
        print(f"BATCH EXPERIMENT RESULTS")
        print(f"{'='*60}")
        print(f"Batch Size:                  {len(failed_txns)}")
        print(f"Eligible Cases:              {results['eligible']}")
        print(f"Predictions Generated:       {results['predicted']}")
        print(f"Recommendations Generated:   {results['recommended']}")
        print(f"Policy Blocked:              {results['policy_blocked']}")
        print(f"Auto-Executed:               {results['auto_executed']}")
        print(f"Escalated:                   {results['escalated']}")
        print(f"Successful Recoveries:       {results['recovered']}")
        print(f"Failed Actions:              {results['failed']}")
        print(f"Recovered Revenue:           ₹{results['recovered_revenue']:,.2f}")
        print(f"Revenue at Risk:             ₹{results['revenue_at_risk']:,.2f}")
        print(f"Recovery Rate:               {recovery_rate:.2f}%")
        print(f"Revenue Recovery Rate:       {revenue_recovery:.2f}%")
        print(f"Avg Latency per Transaction: {avg_latency*1000:.2f}ms")
        print(f"\nBaseline (rule-only) Rate:   {baseline_rate:.2f}%")
        print(f"{'='*60}\n")

        report = get_batch_recovery_report()
        report_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'generated', 'batch_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to {report_path}")


if __name__ == '__main__':
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    run_batch_experiment(batch_size)
