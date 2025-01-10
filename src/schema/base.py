from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict


def serialize_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


class BaseSchema(BaseModel):
    """Base schema for all Lumeo models with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={datetime: serialize_datetime}
    )