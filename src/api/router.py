from fastapi import APIRouter
from src.api.endpoints.v1.generation import router as generation_router


router = APIRouter(prefix="/api/v1")

router.include_router(generation_router) 