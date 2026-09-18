"""Tests for the health endpoint."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.presentation.helpers import make_test_app


class TestHealthEndpoint:
    def test_health(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["data"] == {"service": "healthy"}
