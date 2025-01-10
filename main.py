import logging
from modal import asgi_app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import modal

from src.common import ai_image, volumes, secrets
from src.api.functions import app as functions_app
from src.api.router import router as api_v1_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = modal.App(name="learn-anything")

app.include(functions_app)

@app.function(image=ai_image, volumes=volumes, secrets=secrets)
@asgi_app()
def api():
    api = FastAPI(
        title="Learn Anything",
        openapi_url=f"/api/v1/openapi.json",
    )

    api.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    # Include API v1 router
    api.include_router(api_v1_router)
    
    return api