import os
import modal
import logging
from src.common import sandbox_image, ai_image, secrets, volumes
from src.agents.scene_builder import SceneBuilder
from src.agents.lecture_planner import LecturePlanner, Slide
from src.services.voiceover_service import embed_audio_and_subtitles, generate_audio, add_voiceover_and_subtitles, merge_videos

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = modal.App(name="learn-anything")


@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def test_scene_builder():
    """Test the SceneBuilder agent with a simple concept."""
    try:
        logger.info("Starting scene builder test")

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

        # Example learning content
        description = "Introduction to Python Variables"
        voiceover = "Variables in Python are like containers that store data. When we create a variable, Python allocates memory to store its value."
        details = """
        Create a visual scene that shows:
        1. A container/box representing a variable
        2. Text showing variable name 'x'
        3. An arrow pointing from 'x' to the container
        4. The number 42 appearing inside the container
        5. Text showing 'x = 42' at the bottom
        
        The animation should:
        1. First show the empty container
        2. Then show the variable name
        3. Draw the arrow
        4. Finally show the value 42 appearing inside
        
        Keep the scene simple and focused on these core elements.
        Use basic shapes and clear animations.
        """

        result = builder.generate_scene(
            description=description,
            voiceover=voiceover,
            details=details,
            output_path="/data/python_variables.mp4"
        )

        logger.info(
            f"Scene generated successfully after {result['iterations']} iterations")
        logger.info("\nGenerated Scene Code:")
        logger.info(result['scene_code'])

        # Clean up
        sandbox.terminate()

        return result

    except Exception as e:
        logger.error(f"Error in scene generation: {str(e)}", exc_info=True)
        raise


@app.function(volumes=volumes)
def test_manim():
    print("Hello World Manim")
    sb = modal.Sandbox.create(app=app, image=sandbox_image, volumes=volumes)

    with sb.open("/data/scene.py", "w") as f:
        f.write("""from manim import *
class CreateCircle(Scene):
    def construct(self):
        circle = Circle()
        circle.set_fill(PINK, opacity=0.5)
        self.play(Create(circle))""")

    b = sb.exec("manim", "render", "-ql",
                "/data/scene.py", "-o", "/data/output.mp4")
    print(b.stdout.read())
    print(b.stderr.read())

    print(sb.exec("ls", "-la", "/data").stdout.read())
    print(sb.exec("ls", "-la", "/data").stderr.read())


@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def test_subtitle_service():
    # Create sandbox first
    sandbox = modal.Sandbox.create(
        image=sandbox_image,
        app=app,
        volumes=volumes
    )

    add_voiceover_and_subtitles(
        sandbox=sandbox, video_path="/data/output.mp4",
        voiceover_text="Variables in Python are like containers that store data. When we create a variable, Python allocates memory to store its value. ariables in Python are like containers that store data. When we create a variable, Python allocates memory to store its value.",
        output_video_path="/data/output_with_voiceover.mp4"
    )
    
    



@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def generate_slide(slide: Slide, title: str, slide_id: int):
    try:
        logger.info("Generating slide")

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
def test_lecture_planner():
    """Test the LecturePlanner with a sample topic."""
    try:
        logger.info("Starting lecture planner test")
        
        # Initialize planner
        planner = LecturePlanner()
        
        # Example topic with resources
        topic = "How does gene therapy work?"
        resources = """

        """
        
        # Generate lecture plan
        lecture_plan = planner.plan_lecture(topic, resources)
        
        # Log the results
        logger.info(f"\nGenerated Lecture Plan: {lecture_plan.title}")
        for i, slide in enumerate(lecture_plan.slides, 1):
            logger.info(f"\nSlide {i}:")
            logger.info(f"Voiceover: {slide.voiceover}")
            logger.info(f"Description: {slide.description}")
        
        # Generate slides
        params = [(slide, lecture_plan.title, i) for i, slide in enumerate(lecture_plan.slides)]
        for res in generate_slide.starmap(params, return_exceptions=True):
            logger.info(res)
        
        return lecture_plan
        
    except Exception as e:
        logger.error(f"Error in lecture planning: {str(e)}", exc_info=True)
        raise


@app.function(image=ai_image, volumes=volumes, secrets=secrets)
def debug():
    sandbox = modal.Sandbox.create(
        image=sandbox_image,
        app=app,
        volumes=volumes
    )
    
    video_paths = [f"/data/slide_{slide_id}_with_voiceover.mp4" for slide_id in range(5)]
    merge_videos(sandbox, video_paths, "/data/merged_video.mp4")
    
    # for i in range(5):
    #     slide_id = str(i)
    #     final_video = embed_audio_and_subtitles(sandbox, f"/data/slide_{slide_id}.mp4", f"/data/voiceover_{slide_id}.mp3", f"/data/subtitles_{slide_id}.vtt", f"/data/slide_{slide_id}_with_voiceover.mp4")
    # Clean up
    sandbox.terminate()

@app.local_entrypoint()
def main():
    # test_lecture_planner.remote()
    # test_subtitle_service.remote()
    # logger.info("Starting main application")
    # result = test_scene_builder.remote()
    # logger.info("Scene generation completed")
    debug.remote()
