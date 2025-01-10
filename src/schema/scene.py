from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.schema.base import BaseSchema

class SceneStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Scene(BaseSchema):
    id: Optional[str] = None
    user_id: Optional[str] = None
    lecture_id: Optional[str] = None
    
    status: SceneStatus = SceneStatus.PROCESSING
    index: Optional[int] = None
    version: Optional[int] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    description: Optional[str] = None
    voiceover: Optional[str] = None
    
    user_prompt: Optional[str] = None
    
    
    code: Optional[str] = None
    
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    
    