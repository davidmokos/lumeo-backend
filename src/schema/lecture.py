from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.schema.base import BaseSchema

class LectureStatus(str, Enum):
    PROCESSING = "processing"
    DRAFT = "draft"
    PUBLISHED = "published"

class Lecture(BaseSchema):
    id: Optional[str] = None
    user_id: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    topic: Optional[str] = None
    resources: Optional[str] = None
    
    title: Optional[str] = None
    status: LectureStatus = LectureStatus.PROCESSING
    
    voice_id: Optional[str] = None
    language: Optional[str] = None
    
    video_url: Optional[str] = None
    subtitles_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    