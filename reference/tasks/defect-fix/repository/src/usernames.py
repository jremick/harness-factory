"""Username normalization."""

import re


def normalize_username(value: str) -> str:
    """Normalize a human-entered username."""

    if not isinstance(value, str):
        raise ValueError("username must be a string")
    # BUG: replaces characters individually and keeps boundary separators.
    return re.sub(r"[^a-z0-9]", "-", value.lower())
