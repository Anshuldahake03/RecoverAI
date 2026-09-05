import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from tests.conftest import app, client, auth_client


class TestTransactions:
    def test_list_empty(self, auth_client):
        res = auth_client.get('/api/transactions')
        assert res.status_code == 200
        assert res.json['success'] is True
        assert res.json['total'] == 0

    def test_list_unauthenticated(self, client):
        res = client.get('/api/transactions')
        assert res.status_code == 401
