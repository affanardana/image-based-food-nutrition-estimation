"""Tests for the image dimension parser."""

from app.presentation.image_info import read_image_dimensions
from tests.presentation.helpers import make_jpeg_bytes, make_png_bytes


class TestReadImageDimensions:
    def test_png_dimensions(self) -> None:
        assert read_image_dimensions(make_png_bytes(100, 50)) == (100, 50)

    def test_png_other_dimensions(self) -> None:
        assert read_image_dimensions(make_png_bytes(640, 480)) == (640, 480)

    def test_jpeg_dimensions(self) -> None:
        assert read_image_dimensions(make_jpeg_bytes(80, 40)) == (80, 40)

    def test_jpeg_other_dimensions(self) -> None:
        assert read_image_dimensions(make_jpeg_bytes(1024, 768)) == (1024, 768)

    def test_unknown_format_returns_none(self) -> None:
        assert read_image_dimensions(b"not an image") is None

    def test_truncated_png_returns_none(self) -> None:
        assert read_image_dimensions(b"\x89PNG\r\n\x1a\nshort") is None

    def test_truncated_jpeg_returns_none(self) -> None:
        assert read_image_dimensions(b"\xff\xd8") is None
