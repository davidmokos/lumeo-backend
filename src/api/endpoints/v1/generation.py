from src.api.functions import generate_lecture_function
from src.schema.lecture import Lecture
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/generate", tags=["generation"])


# ---------------------------

class LectureGenerationRequest(BaseModel):
    """Request model for lecture generation"""
    topic: str
    resources: Optional[str] = None


class LectureGenerationResponse(BaseModel):
    """Response model for lecture generation"""
    lecture_id: str


@router.post("/{uid}/lecture", response_model=LectureGenerationResponse)
async def generate_lecture(
    uid: str,
    request: LectureGenerationRequest,
) -> LectureGenerationResponse:
    
    # Create lecture in the database and obtain the id
    
    
    # Spawn a generate_lecture_function
    generate_lecture_function.spawn(request.topic, request.resources)
    
    # return the lecture id
    return LectureGenerationResponse(lecture_id=...)
