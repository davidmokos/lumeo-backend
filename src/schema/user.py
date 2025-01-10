from datetime import datetime
from typing import Optional
from pydantic import Field

from src.schema.base import BaseSchema


class User(BaseSchema):
    """User model with all fields. Some are optional for creation/update."""
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    email: str
    username: str
