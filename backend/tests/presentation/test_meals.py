"""Tests for the meal endpoints — the full API workflow."""

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from app.presentation.api import create_app
from tests.presentation.helpers import (
    make_png_bytes,
    make_test_app,
    make_test_dependencies,
)

IMAGE_FILE = {"image": ("plate.png", make_png_bytes(100, 50), "image/png")}


def analyze(
    client: TestClient,
    suggest_labels: bool = False,
) -> dict[str, Any]:
    """Upload an image and return the parsed response body."""
    data = {"suggest_labels": "true"} if suggest_labels else None
    response = client.post("/api/v1/meals/analyze", files=IMAGE_FILE, data=data)
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


class TestAnalyzeMealEndpoint:
    def test_analyze_returns_draft_with_segments(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            body = analyze(client)

        assert body["status"] == "success"
        data = body["data"]
        assert data["state"] == "draft"
        assert len(data["segments"]) == 2
        assert data["food_items"] == []
        assert data["summary"]["total_calories_kcal"] == 0.0
        # Suggestions disabled by default
        assert all(s["suggestion"] is None for s in data["segments"])
        assert data["image"] == {"width": 100, "height": 50}
        assert data["image_url"].startswith("/api/v1/images/meal_")
        assert data["image_url"].endswith("_plate.png")

    def test_analyze_with_suggestions(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            body = analyze(client, suggest_labels=True)

        segments = body["data"]["segments"]
        assert segments[0]["suggestion"] == {
            "label": "sate",
            "confidence": 0.87,
        }
        assert segments[1]["suggestion"] == {
            "label": "lontong",
            "confidence": 0.87,
        }

    def test_analyze_rejects_unsupported_type(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/meals/analyze",
                files={"image": ("note.txt", b"hello", "text/plain")},
            )

        assert response.status_code == 415
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "UNSUPPORTED_IMAGE"

    def test_analyze_rejects_oversized_image(self, tmp_path: Path) -> None:
        deps, _, _ = make_test_dependencies(tmp_path, max_upload_size_mb=0)
        app = create_app(deps)
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/meals/analyze",
                files={"image": ("big.png", b"x", "image/png")},
            )

        assert response.status_code == 413
        assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"


class TestLabelMealEndpoint:
    def test_label_creates_food_item(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.post(
                f"/api/v1/meals/{meal_id}/label",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_001", "seg_002"],
                        }
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["state"] == "corrected"
        assert len(data["food_items"]) == 1
        item = data["food_items"][0]
        assert item["canonical_food"] == {"id": "sate", "name": "Sate"}
        assert item["segment_ids"] == ["seg_001", "seg_002"]
        assert item["measurement"]["estimated_weight_g"] == 100.0
        assert item["nutrition"]["calories_kcal"] == 218.0
        assert data["summary"]["total_calories_kcal"] == 218.0

    def test_label_unknown_meal(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/meals/missing/label",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_001"],
                        }
                    ]
                },
            )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MEAL_NOT_FOUND"

    def test_label_unknown_food(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.post(
                f"/api/v1/meals/{meal_id}/label",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "bakso",
                            "segment_ids": ["seg_001"],
                        }
                    ]
                },
            )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FOOD_NOT_FOUND"

    def test_label_can_name_the_meal(self, tmp_path: Path) -> None:
        """The name travels with the labels, so it cannot be forgotten."""
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.post(
                f"/api/v1/meals/{meal_id}/label",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_001"],
                        }
                    ],
                    "name": "Lunch with the team",
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Lunch with the team"
        assert len(data["food_items"]) == 1

    def test_label_without_a_name_keeps_the_existing_one(
        self,
        tmp_path: Path,
    ) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]
            client.patch(f"/api/v1/meals/{meal_id}", json={"name": "Dinner"})

            response = client.post(
                f"/api/v1/meals/{meal_id}/label",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_001"],
                        }
                    ]
                },
            )

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Dinner"


class TestGetMealEndpoint:
    def test_get_meal(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.get(f"/api/v1/meals/{meal_id}")

        assert response.status_code == 200
        assert response.json()["data"]["meal_id"] == meal_id

    def test_get_missing_meal(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.get("/api/v1/meals/missing")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MEAL_NOT_FOUND"


class TestCorrectMealEndpoint:
    def test_patch_recalculates_nutrition(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]
            labeled = client.post(
                f"/api/v1/meals/{meal_id}/label",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_001", "seg_002"],
                        }
                    ]
                },
            ).json()
            food_id = labeled["data"]["food_items"][0]["id"]

            response = client.patch(
                f"/api/v1/meals/{meal_id}",
                json={
                    "food_items": [
                        {"id": food_id, "estimated_weight_g": 50.0}
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        item = data["food_items"][0]
        assert item["measurement"]["estimated_weight_g"] == 50.0
        # 218 kcal/100g × 0.5 = 109.0
        assert item["nutrition"]["calories_kcal"] == 109.0
        assert data["summary"]["total_calories_kcal"] == 109.0


class TestDeleteMealEndpoint:
    def test_delete_meal(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.delete(f"/api/v1/meals/{meal_id}")

        assert response.status_code == 200
        assert response.json()["data"] == {"deleted": True}

    def test_delete_missing_meal(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.delete("/api/v1/meals/missing")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MEAL_NOT_FOUND"


class TestMealHistoryEndpoint:
    def test_lists_analyzed_meals_newest_first(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            first = analyze(client)["data"]["meal_id"]
            second = analyze(client)["data"]["meal_id"]

            response = client.get("/api/v1/meals")

        assert response.status_code == 200
        entries = response.json()["data"]
        assert [entry["meal_id"] for entry in entries] == [second, first]
        assert entries[0]["state"] == "draft"
        assert entries[0]["segment_count"] == 2
        assert entries[0]["food_item_count"] == 0
        assert entries[0]["total_calories_kcal"] == 0.0
        assert entries[0]["image_url"].startswith("/api/v1/images/meal_")
        assert entries[0]["created_at"] is not None

    def test_entry_reflects_labeling(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]
            client.post(
                f"/api/v1/meals/{meal_id}/label",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_001", "seg_002"],
                        }
                    ]
                },
            )

            entries = client.get("/api/v1/meals").json()["data"]

        assert entries[0]["food_item_count"] == 1
        assert entries[0]["total_calories_kcal"] > 0.0

    def test_empty_history(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.get("/api/v1/meals")

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_limit_is_validated(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.get("/api/v1/meals?limit=0")

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_meals_endpoint_does_not_shadow_detail(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.get(f"/api/v1/meals/{meal_id}")

        assert response.status_code == 200
        assert response.json()["data"]["meal_id"] == meal_id


class TestDiscardSegmentsEndpoint:
    def test_discard_one_segment(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.post(
                f"/api/v1/meals/{meal_id}/segments/discard",
                json={"segment_ids": ["seg_001"]},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert [segment["id"] for segment in data["segments"]] == ["seg_002"]
        assert data["meal_id"] == meal_id

    def test_discard_several_segments_at_once(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.post(
                f"/api/v1/meals/{meal_id}/segments/discard",
                json={"segment_ids": ["seg_001", "seg_002"]},
            )

        assert response.status_code == 200
        assert response.json()["data"]["segments"] == []

    def test_discard_unknown_segment(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.post(
                f"/api/v1/meals/{meal_id}/segments/discard",
                json={"segment_ids": ["seg_999"]},
            )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_REQUEST"

    def test_discard_empty_list_is_rejected(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.post(
                f"/api/v1/meals/{meal_id}/segments/discard",
                json={"segment_ids": []},
            )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_REQUEST"

    def test_discard_from_unknown_meal(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/meals/missing/segments/discard",
                json={"segment_ids": ["seg_001"]},
            )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MEAL_NOT_FOUND"


class TestRenameMealEndpoint:
    def test_patch_with_only_a_name(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.patch(
                f"/api/v1/meals/{meal_id}",
                json={"name": "Lunch with the team"},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Lunch with the team"
        # Renaming must not disturb the analyzed segments or the state
        assert len(data["segments"]) == 2
        assert data["state"] == "draft"

    def test_name_appears_in_history(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]
            client.patch(
                f"/api/v1/meals/{meal_id}",
                json={"name": "Breakfast"},
            )

            entries = client.get("/api/v1/meals").json()["data"]

        assert entries[0]["name"] == "Breakfast"

    def test_unnamed_meal_has_empty_name(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)

            entries = client.get("/api/v1/meals").json()["data"]

        assert analyzed["data"]["name"] == ""
        assert entries[0]["name"] == ""


class TestReplaceLabelsEndpoint:
    def test_put_rebuilds_the_labeling(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]
            client.post(
                f"/api/v1/meals/{meal_id}/label",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_001"],
                        }
                    ]
                },
            )

            response = client.put(
                f"/api/v1/meals/{meal_id}/labels",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "lontong",
                            "segment_ids": ["seg_001", "seg_002"],
                        }
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["food_items"]) == 1
        item = data["food_items"][0]
        assert item["canonical_food"] == {"id": "lontong", "name": "Lontong"}
        assert item["segment_ids"] == ["seg_001", "seg_002"]
        assert data["state"] == "corrected"

    def test_put_unknown_meal(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            response = client.put(
                "/api/v1/meals/missing/labels",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_001"],
                        }
                    ]
                },
            )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MEAL_NOT_FOUND"

    def test_put_unknown_food(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.put(
                f"/api/v1/meals/{meal_id}/labels",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "bakso",
                            "segment_ids": ["seg_001"],
                        }
                    ]
                },
            )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FOOD_NOT_FOUND"

    def test_put_unknown_segment_is_rejected(self, tmp_path: Path) -> None:
        app = make_test_app(tmp_path)
        with TestClient(app) as client:
            analyzed = analyze(client)
            meal_id = analyzed["data"]["meal_id"]

            response = client.put(
                f"/api/v1/meals/{meal_id}/labels",
                json={
                    "assignments": [
                        {
                            "canonical_food_id": "sate",
                            "segment_ids": ["seg_999"],
                        }
                    ]
                },
            )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
