import modal
import asyncio
from src.common import ai_image, volumes, secrets, sandbox_image
from src.agents.lecture_planner import LecturePlanner
from src.agents.scene_builder import SceneBuilder
from src.agents.lecture_planner import Slide
from src.database.scene_repository import SceneRepository
from src.schema.lecture import Lecture, LectureStatus
from src.database.lecture_repository import LectureRepository
from src.database.storage import StorageClient, StorageBucket
from src.schema.scene import Scene, SceneStatus
from src.services.voiceover_service import add_voiceover_and_subtitles, merge_videos
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = modal.App(name="learn-anything-functions")


@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def merge_scenes_function(lecture: Lecture, scenes: list[Scene]) -> Lecture:
    try:
        logger.info(f"Starting video merge for lecture {lecture.id}")
        lecture_repo = LectureRepository()
        storage = StorageClient()

        # Download videos
        video_paths = []
        for scene in scenes:
            if not scene.video_url:
                logger.warning(f"Scene {scene.id} has no video, skipping")
                continue
            
            local_path = f"/data/scene_{scene.id}_full.mp4"
            storage.download_file(scene.video_url, local_path)
            video_paths.append(local_path)

        if not video_paths:
            raise ValueError("No videos available to merge")

        # Merge videos
        merged_video_path = f"/data/lecture_{lecture.id}.mp4"
        
        sandbox = modal.Sandbox.create(
            image=sandbox_image,
            app=app,
            volumes=volumes
        )
        
        merge_videos(sandbox, video_paths, merged_video_path)
        logger.info("Videos merged successfully")

        sandbox.terminate()

        # Upload merged video
        video_url = storage.upload_file(
            merged_video_path,
            f"lectures/{lecture.id}/final.mp4",
            bucket=StorageBucket.VIDEOS
        )

        # Update lecture
        lecture = lecture_repo.update(lecture.id, {
            "video_url": video_url,
            "status": LectureStatus.DRAFT
        })
        
        logger.info(f"Lecture {lecture.id} merged successfully")
        return lecture

    except Exception as e:
        logger.error(f"Error merging scenes: {str(e)}", exc_info=True)
        raise

@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def generate_scene_function(lecture: Lecture, scene: Scene) -> Scene:
    try:
        logger.info(f"Generating scene {scene.id}")

        # Create sandbox first
        sandbox = modal.Sandbox.create(
            image=sandbox_image,
            app=app,
            volumes=volumes
        )

        # Initialize builder with sandbox
        builder = SceneBuilder(
            sandbox=sandbox
        )

        result = builder.generate_scene(
            lecture=lecture,
            scene=scene
        )

        logger.info(f"Scene {scene.id} generated successfully")


        # Clean up
        sandbox.terminate()

        return result

    except Exception as e:
        logger.error(f"Error in scene generation: {str(e)}", exc_info=True)
        scene_repo = SceneRepository()
        scene_repo.update(scene.id, {"status": SceneStatus.FAILED})
        raise


@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def generate_lecture_function(lecture: Lecture):
    """Generate a lecture"""
    try:
        logger.info(f"Starting lecture generation for topic: {lecture.topic}")
        lecture_repo = LectureRepository()
        scene_repo = SceneRepository()
        
        # Create lecture plan
        planner = LecturePlanner()
        lecture_plan = planner.plan_lecture(lecture.topic, lecture.resources)
        lecture_repo.update(lecture.id, {"title": lecture_plan.title})
        
        # Create empty scenes
        scenes = []
        for i, slide in enumerate(lecture_plan.slides):
            scene = Scene(
                user_id=lecture.user_id,
                lecture_id=lecture.id,
                status=SceneStatus.PROCESSING,
                index=i,
                version=1,
                description=slide.description,
                voiceover=slide.voiceover,
            )
            created_scene = scene_repo.create(scene)
            scenes.append(created_scene)
         
        # Generate scenes
        generated_scenes = []
        for res in generate_scene_function.starmap(map(lambda s: (lecture, s), scenes), return_exceptions=True):
            if isinstance(res, Scene):
                logger.info(f"Scene {res.id} generated successfully")
                generated_scenes.append(res)
            else:
                logger.error(f"Error generating scene: {res}")
        
        merge_scenes_function.remote(lecture, generated_scenes)
        
        logger.info("Lecture generation complete")
        
    except Exception as e:
        logger.error(f"Error in lecture generation: {str(e)}")
        raise



@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def debug_function():
    lecture_repo = LectureRepository()
    scene_repo = SceneRepository()
    
    lecture = lecture_repo.get("0cf35e16-2b2c-4903-8add-c71252d23fae")
    scene = scene_repo.get("c1655081-6e58-4e9c-b406-e2ef0248d638")
    
    
    sandbox = modal.Sandbox.create(
        image=sandbox_image,
        app=app,
        volumes=volumes
    )

    # Initialize builder with sandbox
    builder = SceneBuilder(
        sandbox=sandbox
    )

    result = builder.generate_scene(
        lecture=lecture,
        scene=scene
    )
    
    # generate_scene_function.remote(
    #     lecture=lecture,
    #     scene=scene
    # )

@app.local_entrypoint()
def main():
    debug_function.remote()