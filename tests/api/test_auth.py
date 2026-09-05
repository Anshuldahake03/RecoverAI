import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from tests.conftest import app, client, auth_client


class TestAuth:
    def test_register(self, client):
        res = client.post('/api/auth/register', json={'email': 'new@test.com', 'password': 'pass123'})
        assert res.status_code == 201
        assert res.json['success'] is True

    def test_register_duplicate(self, client):
        client.post('/api/auth/register', json={'email': 'dup@test.com', 'password': 'pass123'})
        res = client.post('/api/auth/register', json={'email': 'dup@test.com', 'password': 'pass123'})
        assert res.status_code == 409

    def test_login(self, client):
        client.post('/api/auth/register', json={'email': 'login@test.com', 'password': 'pass123'})
        res = client.post('/api/auth/login', json={'email': 'login@test.com', 'password': 'pass123'})
        assert res.status_code == 200
        assert res.json['success'] is True

    def test_login_invalid(self, client):
        res = client.post('/api/auth/login', json={'email': 'x@test.com', 'password': 'wrong'})
        assert res.status_code == 401

    def test_me_authenticated(self, auth_client):
        res = auth_client.get('/api/auth/me')
        assert res.status_code == 200
        assert res.json['success'] is True

    def test_me_unauthenticated(self, client):
        res = client.get('/api/auth/me')
        assert res.status_code == 401

    def test_logout(self, auth_client):
        res = auth_client.post('/api/auth/logout')
        assert res.status_code == 200
