from datetime import UTC, datetime
from typing import Annotated

from pydantic.functional_serializers import PlainSerializer


def _serialize_utc_datetime(v: datetime | None) -> str | None:
    if v is None:
        return None
    if v.tzinfo is None:
        v = v.replace(tzinfo=UTC)
    return v.isoformat()


UTCDatetime = Annotated[datetime, PlainSerializer(_serialize_utc_datetime)]
