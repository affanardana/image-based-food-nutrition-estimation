"""Tests for ConfidenceScore value object."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.values.confidence_score import ConfidenceScore


class TestConfidenceScore:
    def test_valid_confidence(self) -> None:
        cs = ConfidenceScore(0.85)
        assert cs.value == 0.85

    def test_zero_confidence(self) -> None:
        cs = ConfidenceScore(0.0)
        assert cs.value == 0.0

    def test_one_confidence(self) -> None:
        cs = ConfidenceScore(1.0)
        assert cs.value == 1.0

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            ConfidenceScore(-0.1)

    def test_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            ConfidenceScore(1.01)

    def test_percentage_property(self) -> None:
        cs = ConfidenceScore(0.85)
        assert cs.percentage == 85.0

    def test_str_format(self) -> None:
        cs = ConfidenceScore(0.96)
        assert "96" in str(cs)

    def test_immutable(self) -> None:
        cs = ConfidenceScore(0.5)
        with pytest.raises(FrozenInstanceError):
            cs.value = 0.8  # type: ignore[misc]

    def test_equality(self) -> None:
        assert ConfidenceScore(0.5) == ConfidenceScore(0.5)

    def test_inequality(self) -> None:
        assert ConfidenceScore(0.5) != ConfidenceScore(0.6)
