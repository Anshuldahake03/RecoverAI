import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, \
    confusion_matrix, classification_report
from sklearn.preprocessing import LabelEncoder
import logging

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'generated')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.pkl')
METRICS_PATH = os.path.join(MODEL_DIR, 'metrics.pkl')

method_encoder = LabelEncoder()
failure_encoder = LabelEncoder()
method_encoder.fit(['upi', 'card', 'netbanking', 'wallet', 'emi'])
failure_encoder.fit([
    'temporary_failure', 'insufficient_funds', 'card_expired',
    'authentication_failed', 'technical_error', 'bank_declined'
])


def prepare_features(df):
    features = pd.DataFrame()
    features['amount'] = df['amount']
    features['payment_method'] = method_encoder.transform(df['payment_method'])
    features['failure_reason'] = failure_encoder.transform(df['failure_reason'])
    features['retry_count'] = df['retry_count']
    features['customer_successful_count'] = df.get('previous_success_count', pd.Series([0] * len(df)))
    features['customer_failed_count'] = df.get('previous_failure_count', pd.Series([0] * len(df)))
    features['historical_success_rate'] = df.get('historical_success_rate', pd.Series([0.5] * len(df)))
    features['account_age_days'] = df.get('account_age_days', pd.Series([30] * len(df)))
    return features


def train_model(data_path=None):
    if data_path is None:
        data_path = os.path.join(MODEL_DIR, 'synthetic_dataset.csv')

    if not os.path.exists(data_path):
        logger.error(f"Dataset not found at {data_path}")
        return None

    df = pd.read_csv(data_path)
    logger.info(f"Loaded {len(df)} records from {data_path}")

    X = prepare_features(df)
    y = df['recovery_success'].astype(int)

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

    logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    models = {
        'logistic_regression': LogisticRegression(max_iter=1000, random_state=42),
        'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'gradient_boosting': GradientBoostingClassifier(n_estimators=100, random_state=42)
    }

    best_model = None
    best_f1 = 0
    best_name = None
    all_metrics = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        y_proba = model.predict_proba(X_val)[:, 1]

        precision = precision_score(y_val, y_pred, zero_division=0)
        recall = recall_score(y_val, y_pred, zero_division=0)
        f1 = f1_score(y_val, y_pred, zero_division=0)
        try:
            auc = roc_auc_score(y_val, y_proba)
        except ValueError:
            auc = 0.0

        all_metrics[name] = {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
            'roc_auc': round(auc, 4)
        }

        logger.info(f"{name}: P={precision:.4f} R={recall:.4f} F1={f1:.4f} AUC={auc:.4f}")

        if f1 > best_f1:
            best_f1 = f1
            best_model = model
            best_name = name

    y_test_pred = best_model.predict(X_test)
    y_test_proba = best_model.predict_proba(X_test)[:, 1]

    test_metrics = {
        'model_name': best_name,
        'precision': round(precision_score(y_test, y_test_pred, zero_division=0), 4),
        'recall': round(recall_score(y_test, y_test_pred, zero_division=0), 4),
        'f1': round(f1_score(y_test, y_test_pred, zero_division=0), 4),
        'roc_auc': round(roc_auc_score(y_test, y_test_proba), 4),
        'confusion_matrix': confusion_matrix(y_test, y_test_pred).tolist(),
        'classification_report': classification_report(y_test, y_test_pred, output_dict=True),
        'all_model_metrics': all_metrics,
        'train_size': len(X_train),
        'val_size': len(X_val),
        'test_size': len(X_test)
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(best_model, f)
    with open(METRICS_PATH, 'wb') as f:
        pickle.dump(test_metrics, f)

    logger.info(f"Best model: {best_name} (F1={best_f1:.4f}), saved to {MODEL_PATH}")
    return test_metrics
