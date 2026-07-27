from __future__ import annotations

import base64
import binascii
import re
from urllib.parse import urlparse

IMAGE_DATA_PATTERN = re.compile(r"^data:image/(jpeg|png|webp);base64,", re.IGNORECASE)
MAX_IMAGE_BYTES = 2 * 1024 * 1024


def validate_image_reference(value: str | None, *, label: str) -> str | None:
    """Accept a small uploaded image data URL and retain legacy HTTPS image references."""

    if value is None or not value.strip():
        return None
    normalized = value.strip()
    match = IMAGE_DATA_PATTERN.match(normalized)
    if match:
        try:
            raw = base64.b64decode(normalized[match.end() :], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError(f"{label} image data is invalid.") from exc
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise ValueError(f"{label} image must be between 1 byte and 2 MB.")
        return normalized

    parsed = urlparse(normalized)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return normalized
    raise ValueError(f"{label} must be an uploaded JPEG, PNG, or WebP image.")
