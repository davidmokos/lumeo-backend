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
async def generate_scene_function(scene: Scene) -> Scene:
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
            description=title,
            voiceover=slide.voiceover,
            details=slide.description,
            output_path=f"/data/slide_{slide_id}.mp4"
        )

        logger.info(
            f"Scene generated successfully after {result['iterations']} iterations")
        logger.info("\nGenerated Scene Code:")
        logger.info(result['scene_code'])
        
        
        add_voiceover_and_subtitles(
            sandbox=sandbox,
            video_path=f"/data/slide_{slide_id}.mp4",
            voiceover_text=slide.voiceover,
            output_video_path=f"/data/slide_{slide_id}_with_voiceover.mp4",
            slide_id=slide_id
        )

        # Clean up
        sandbox.terminate()

        return result

    except Exception as e:
        logger.error(f"Error in scene generation: {str(e)}", exc_info=True)
        raise


@app.function(image=ai_image, volumes=volumes, secrets=secrets)
async def generate_lecture_function(lecture: Lecture):
    """Generate a lecture"""
    try:
        logger.info(f"Starting lecture generation for topic: {lecture.topic}")
        lecture_repo = LectureRepository()
        scene_repo = SceneRepository()
        
        # Create lecture plan
        planner = LecturePlanner()
        lecture_plan = planner.plan_lecture(lecture.topic, lecture.resources)
        await lecture_repo.update(lecture.id, {"title": lecture_plan.title})
        
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
            created_scene = await scene_repo.create(scene)
            scenes.append(created_scene)
         
        # Generate scenes
        generated_scenes = []
        for res in generate_scene_function.map(scenes, return_exceptions=True):
            if isinstance(res, Scene):
                logger.info(f"Scene {res.id} generated successfully")
                generated_scenes.append(res)
            else:
                logger.error(f"Error generating scene {res.id}: {res}")
        
        # Merge all videos
        # TODO: Merge videos
        video_paths = [f"/data/slide_{i}_with_voiceover.mp4" for i in range(len(lecture_plan.slides))]
        merge_videos(sandbox, video_paths, "/data/merged_video.mp4")
        
        # Upload final video
        storage = StorageClient()
        video_url = await storage.upload_file(
            bucket=StorageBucket.LECTURES,
            file_path="/data/merged_video.mp4",
            destination_path=f"{lecture.id}/lecture.mp4"
        )
        
        # Update lecture with video URL and status
        await lecture_repo.update(lecture.id, {
            "video_url": video_url,
            "status": LectureStatus.PUBLISHED
        })
        
        # Clean up
        sandbox.terminate()
        
        logger.info("Lecture generation complete")
        
    except Exception as e:
        logger.error(f"Error in lecture generation: {str(e)}")
        # Update lecture status to failed
        lecture_repo = LectureRepository()
        await lecture_repo.update(lecture.id, {"status": LectureStatus.FAILED})
        raise

@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def generate_scene_function(topic: str, resources: str):
    """Generate a scene"""
    print(f"Generating scene for topic: {topic} with resources: {resources}")