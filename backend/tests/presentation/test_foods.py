"""Tests for the food search endpoint."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.presentation.helpers import make_test_app


class TestFoodSearchEndpoint:
    def test_search_matches(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.get("/api/v1/foods/search", params={"q": "sate"})

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["data"] == [{"id": "sate", "name": "Sate"}]

    def test_search_empty_returns_all(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.get("/api/v1/foods/search", params={"q": ""})

        assert response.status_code == 200
        assert len(response.json()["data"]) == 3

    def test_search_limit_respected(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/foods/search",
                params={"q": "", "limit": 2},
            )

        assert response.status_code == 200
        assert len(response.json()["data"]) == 2
