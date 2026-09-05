import os
import pickle
import logging

logger = logging.getLogger(__name__)

METRICS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'generated', 'metrics.pkl')


def load_metrics():
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
    return None
