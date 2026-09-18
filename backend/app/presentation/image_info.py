"""Minimal PNG/JPEG dimension parsing without external imaging libraries."""

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8"

# JPEG start-of-frame markers that carry dimensions.
_JPEG_SOF_MARKERS = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)


def read_image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Return (width, height) for PNG or JPEG bytes, or None if unknown."""
    if data.startswith(PNG_MAGIC):
        return _png_dimensions(data)
    if data.startswith(JPEG_MAGIC):
        return _jpeg_dimensions(data)
    return None


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    # IHDR chunk: 8-byte signature, then length(4) "IHDR" width(4) height(4).
    if len(data) < 24:
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        return None
    return width, height


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = int.from_bytes(data[i + 2 : i + 4], "big")
        if length < 2:
            return None
        if marker in _JPEG_SOF_MARKERS:
            # SOFn payload: precision(1) height(2) width(2) ...
            height = int.from_bytes(data[i + 5 : i + 7], "big")
            width = int.from_bytes(data[i + 7 : i + 9], "big")
            if width <= 0 or height <= 0:
                return None
            return width, height
        i += 2 + length
    return None
