from __future__ import annotations

import re


def normalize_indian_phone(value: str | None) -> str | None:
    """Accept common Indian mobile formats and store them as E.164 values."""

    if value is None or not str(value).strip():
        return None
    normalized = re.sub(r"[\s()-]", "", str(value))
    if re.fullmatch(r"[6-9][0-9]{9}", normalized):
        return f"+91{normalized}"
    if re.fullmatch(r"0[6-9][0-9]{9}", normalized):
        return f"+91{normalized[1:]}"
    if re.fullmatch(r"91[6-9][0-9]{9}", normalized):
        return f"+{normalized}"
    return normalized
