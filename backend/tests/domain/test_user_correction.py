"""Tests for UserCorrection entity."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.entities.user_correction import UserCorrection


class TestUserCorrection:
    def test_create_correction(self) -> None:
        uc = UserCorrection(
            field="canonical_food",
            old_value="cheeseburger",
            new_value="Burger",
        )
        assert uc.field == "canonical_food"
        assert uc.old_value == "cheeseburger"
        assert uc.new_value == "Burger"

    def test_str_includes_values(self) -> None:
        uc = UserCorrection(
            field="weight",
            old_value="150g",
            new_value="200g",
        )
        s = str(uc)
        assert "weight" in s
        assert "150g" in s
        assert "200g" in s

    def test_has_timestamp(self) -> None:
        uc = UserCorrection(
            field="weight",
            old_value="100g",
            new_value="150g",
        )
        assert uc.timestamp is not None

    def test_immutable(self) -> None:
        uc = UserCorrection(field="weight", old_value="100g", new_value="150g")
        with pytest.raises(FrozenInstanceError):
            uc.field = "other"  # type: ignore[misc]
