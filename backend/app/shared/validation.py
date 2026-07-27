from __future__ import annotations

from typing import Annotated

from bson import ObjectId
from pydantic import AfterValidator


def validate_object_id(value: str) -> str:
    if not ObjectId.is_valid(value):
        raise ValueError("Value must be a valid MongoDB ObjectId.")
    return value


MongoId = Annotated[str, AfterValidator(validate_object_id)]
