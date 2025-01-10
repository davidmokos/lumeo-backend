import modal
import asyncio
from src.common import ai_image, volumes, secrets
app = modal.App(name="learn-anything-functions")

@app.function(image=ai_image, volumes=volumes, secrets=secrets)
async def generate_lecture_function(topic: str, resources: str):
    """Generate a lecture"""
    # wait 2 seconds
    await asyncio.sleep(2)
    print(f"lecture generation complete")

@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def generate_scene_function(topic: str, resources: str):
    """Generate a scene"""
    print(f"Generating scene for topic: {topic} with resources: {resources}")