"""Shared Pydantic field validators used across multiple schema modules."""

import json
from typing import Any


def parse_tools_json(v: Any) -> list[str]:
    """Parse a tools field that may be a JSON string or a list.

    Used as a Pydantic field_validator helper for `tools` fields
    stored as JSON strings in the database.
    """
    if isinstance(v, str):
        parsed: list[str] = json.loads(v)
        return parsed
    return list(v)
