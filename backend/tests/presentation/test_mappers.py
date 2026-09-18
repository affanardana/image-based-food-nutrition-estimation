"""Tests for presentation mappers — storage path → public URL conversion."""

from dataclasses import replace
from pathlib import Path

from app.domain.entities.meal import Meal
from app.presentation.mappers import meal_to_data, stored_path_to_url
from tests.helpers import make_segment


class TestStoredPathToUrl:
    def test_converts_path_under_storage_base(self, tmp_path: Path) -> None:
        base = tmp_path / "storage"
        stored = str(base / "crops" / "seg_001.jpg")

        url = stored_path_to_url(str(base), stored)

        assert url == "/api/v1/images/crops/seg_001.jpg"

    def test_converts_relative_storage_base(self) -> None:
        url = stored_path_to_url("storage", "storage/crops/seg_001.jpg")

        assert url == "/api/v1/images/crops/seg_001.jpg"

    def test_passes_through_url_shaped_references(self) -> None:
        url = stored_path_to_url("/some/base", "/api/v1/images/crops/seg_001.jpg")

        assert url == "/api/v1/images/crops/seg_001.jpg"

    def test_passes_through_without_storage_base(self, tmp_path: Path) -> None:
        stored = str(tmp_path / "crops" / "seg_001.jpg")

        url = stored_path_to_url(None, stored)

        assert url == stored

    def test_passes_through_path_outside_storage_base(self, tmp_path: Path) -> None:
        base = tmp_path / "storage"
        outside = str(tmp_path / "elsewhere" / "crop.jpg")

        url = stored_path_to_url(str(base), outside)

        assert url == outside

    def test_empty_reference_stays_empty(self) -> None:
        assert stored_path_to_url("storage", "") == ""


class TestMealToData:
    def test_segment_crop_urls_are_converted(self, tmp_path: Path) -> None:
        base = tmp_path / "storage"
        stored_crop = str(base / "crops" / "seg_001.jpg")
        segment = replace(make_segment(), crop_image_ref=stored_crop)
        meal = Meal(
            meal_id="meal_1",
            image_path=str(base / "meal_1_plate.png"),
            segments=[segment],
        )

        data = meal_to_data(meal, storage_base=str(base))

        assert data.image_url == "/api/v1/images/meal_1_plate.png"
        assert data.segments[0].crop_url == "/api/v1/images/crops/seg_001.jpg"

    def test_mock_url_references_pass_through(self, tmp_path: Path) -> None:
        segment = replace(
            make_segment(),
            crop_image_ref="/api/v1/images/crops/seg_001.jpg",
        )
        meal = Meal(
            meal_id="meal_1",
            image_path="/storage/meal_1.png",
            segments=[segment],
        )

        data = meal_to_data(meal, storage_base=str(tmp_path / "storage"))

        assert data.segments[0].crop_url == "/api/v1/images/crops/seg_001.jpg"
