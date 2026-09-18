"""Identifier generation helpers."""

import uuid


def generate_id(prefix: str) -> str:
    """Generate a prefixed unique identifier.

    Example:
        generate_id("meal") -> "meal_9f3c2a1b4d5e6f70"
    """
    return f"{prefix}_{uuid.uuid4().hex[:16]}"
