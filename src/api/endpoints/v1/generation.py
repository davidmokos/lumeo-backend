from src.api.functions import generate_lecture_function, generate_lecture_no_plan_function, generate_scene_function, regenerate_scene_function
from src.database.scene_repository import SceneRepository
from src.schema.lecture import Lecture, LectureStatus
from src.database.lecture_repository import LectureRepository
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.schema.scene import Scene, SceneStatus


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
    # Create lecture in the database
    lecture_repo = LectureRepository()
    lecture = Lecture(
        user_id=uid,
        topic=request.topic,
        resources=request.resources,
        status=LectureStatus.PROCESSING
    )
    created_lecture = lecture_repo.create(lecture)
    
    # Spawn a generate_lecture_function
    generate_lecture_function.spawn(created_lecture)
    
    # return the lecture id
    return LectureGenerationResponse(lecture_id=created_lecture.id)

@router.post("/{uid}/lecture/{lecture_id}", response_model=LectureGenerationResponse)
async def generate_lecture(
    uid: str,
    lecture_id: str,
) -> LectureGenerationResponse:
    # Create lecture in the database
    lecture_repo = LectureRepository()
    lecture = lecture_repo.get(lecture_id)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    # Spawn a generate_lecture_function
    generate_lecture_no_plan_function.spawn(lecture)
    
    # return the lecture id
    return LectureGenerationResponse(lecture_id=lecture.id)


class SceneGenerationRequest(BaseModel):
    """Request model for scene generation"""
    user_prompt: str

class SceneGenerationResponse(BaseModel):
    """Response model for scene generation"""
    scene_id: str

@router.post("/{uid}/scene/{scene_id}", response_model=SceneGenerationResponse)
async def generate_scene(
    uid: str,
    scene_id: str,
    request: SceneGenerationRequest,
) -> SceneGenerationResponse:
    scene_repo = SceneRepository()
    scene = scene_repo.get(scene_id)
    
    lecture_repo = LectureRepository()
    lecture = lecture_repo.get(scene.lecture_id)
    
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    new_scene = scene_repo.create(
        Scene(
            user_id=uid,
            lecture_id=scene.lecture_id,
            status=SceneStatus.PROCESSING,
            index=scene.index,
            version=scene.version + 1,
            description=scene.description,
            voiceover=scene.voiceover,
            user_prompt=request.user_prompt,
            code=None,
            audio_url=None,
            video_url=None,
        )
    )
    
    regenerate_scene_function.spawn(lecture, new_scene)
    
    return SceneGenerationResponse(scene_id=new_scene.id)
