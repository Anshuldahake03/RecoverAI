import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from tests.conftest import app, client, auth_client


class TestAnalytics:
    def test_overview(self, auth_client):
        res = auth_client.get('/api/analytics/overview')
        assert res.status_code == 200
        assert res.json['success'] is True
        assert 'total_transactions' in res.json['overview']

    def test_model_metrics(self, auth_client):
        res = auth_client.get('/api/analytics/model')
        assert res.status_code == 200

    def test_unauthenticated(self, client):
        res = client.get('/api/analytics/overview')
        assert res.status_code == 401


class TestRecovery:
    def test_list_empty(self, auth_client):
        res = auth_client.get('/api/recovery')
        assert res.status_code == 200
        assert res.json['success'] is True
