"""
test_server_health.py — Unit tests for the /health and /ready probe endpoints.
"""

import pytest
from starlette.testclient import TestClient
from unittest.mock import patch
from src.server import app


def test_health_check_returns_200():
    """GET /health returns status: healthy with HTTP 200."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "notifications-mcp"


def test_readiness_check_unauthenticated():
    """GET /ready returns 503 when token file does not exist."""
    client = TestClient(app)
    with patch("pathlib.Path.exists", return_value=False):
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "needs_auth"
        assert data["channels"]["mail"] == "unauthenticated"


def test_readiness_check_authenticated():
    """GET /ready returns 200 when token file exists."""
    client = TestClient(app)
    with patch("pathlib.Path.exists", return_value=True):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["channels"]["mail"] == "configured"
