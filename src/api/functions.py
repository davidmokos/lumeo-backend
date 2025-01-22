from datetime import datetime, time
import os
import modal
import asyncio
import requests
from src.common import ai_image, volumes, secrets, sandbox_image
from src.agents.lecture_planner import LecturePlanner
from src.agents.scene_builder import SceneBuilder
from src.agents.lecture_planner import Slide
from src.database.scene_repository import SceneRepository
from src.schema.lecture import Lecture, LectureStatus
from src.database.lecture_repository import LectureRepository
from src.database.storage import StorageClient, StorageBucket
from src.schema.scene import Scene, SceneStatus
from src.services.voiceover_service import add_voiceover_and_subtitles, create_empty_video, get_last_frame, merge_videos
import logging
from src.common import vol
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

        vol.reload()
        # Download videos
        video_paths = []
        for scene in scenes:
            if not scene.video_url:
                logger.warning(f"Scene {scene.id} has no video, skipping")
                continue
            
            local_path = f"/data/scene_{scene.id}_full.mp4"
            if os.path.exists(local_path):
                logger.info(f"Scene {scene.id} video already exists, skipping download")
                video_paths.append(local_path)
                continue
            
            response = requests.get(scene.video_url, stream=True)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            video_paths.append(local_path)
        
        vol.commit()
        vol.reload()

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
        
        last_frame_path = f"/data/lecture_{lecture.id}_last_frame.png"
        get_last_frame(sandbox, video_paths[0], last_frame_path)

        sandbox.terminate()

        # Upload merged video
        vol.reload()
        video_url = storage.upload_file(
            bucket=StorageBucket.LECTURES,
            file_path=merged_video_path,
            destination_path=f"{lecture.id}/{datetime.now().strftime('%Y%m%d%H%M%S')}-final.mp4"
        )
        
        try:
            last_frame_url = storage.upload_file(
                bucket=StorageBucket.LECTURES,
                file_path=last_frame_path,
                destination_path=f"{lecture.id}/{datetime.now().strftime('%Y%m%d%H%M%S')}-last_frame.png"
            )
        except Exception as e:
            logger.error(f"Error uploading last frame: {str(e)}")
            last_frame_url = None

        # Update lecture
        lecture = lecture_repo.update(lecture.id, {
            "video_url": video_url,
            "thumbnail_url": last_frame_url,
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
        for i, slide in enumerate(lecture_plan.slides, start=1):
            scene = Scene(
                user_id=lecture.user_id,
                lecture_id=lecture.id,
                status=SceneStatus.PROCESSING,
                index=i,
                version=1,
                is_selected=True,
                description=slide.description,
                voiceover=slide.voiceover,
            )
            created_scene = scene_repo.create(scene)
            scenes.append(created_scene)
         
        # Generate scenes
        generated_scenes = []
        for res in generate_scene_function.starmap(map(lambda s: (lecture, s), scenes), return_exceptions=True):
            if isinstance(res, Scene):
                generated_scenes.append(res)
            else:
                logger.error(f"Error generating scene: {res}")
                
        generated_scenes.sort(key=lambda x: x.index)
        
        merge_scenes_function.remote(lecture, generated_scenes)
        
        logger.info("Lecture generation complete")
        
    except Exception as e:
        logger.error(f"Error in lecture generation: {str(e)}")
        raise


@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def generate_lecture_no_plan_function(lecture: Lecture):
    """Generate a lecture without a plan"""
    try:
        logger.info(f"Starting lecture generation for topic: {lecture.topic}")
        lecture_repo = LectureRepository()
        scene_repo = SceneRepository()
        

        lecture_repo.update(lecture.id, {"status": LectureStatus.PROCESSING})
        
        scenes = scene_repo.list_by_lecture(lecture_id=lecture.id)
         
        # Generate scenes
        generated_scenes = []
        for res in generate_scene_function.starmap(map(lambda s: (lecture, s), scenes), return_exceptions=True):
            if isinstance(res, Scene):
                generated_scenes.append(res)
            else:
                logger.error(f"Error generating scene: {res}")
        
        merge_scenes_function.remote(lecture, generated_scenes)
        
        logger.info("Lecture generation complete")
        
    except Exception as e:
        logger.error(f"Error in lecture generation: {str(e)}")
        raise


@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def regenerate_scene_function(lecture: Lecture, scene: Scene):
    generate_scene_function.remote(lecture, scene)
    
    scene_repo = SceneRepository()
    scenes = scene_repo.list_by_lecture(lecture_id=lecture.id)
    
    # Group scenes by index and get the highest version for each
    latest_scenes = {}
    for s in scenes:
        if s.index not in latest_scenes or s.version > latest_scenes[s.index].version:
            latest_scenes[s.index] = s
    
    # Convert to list and sort by index
    sorted_scenes = sorted(latest_scenes.values(), key=lambda x: x.index)
    
    merge_scenes_function.remote(lecture, sorted_scenes)
