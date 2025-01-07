import os
import modal
import logging
from src.common import sandbox_image, ai_image, secrets, volumes
from src.scene_builder import SceneBuilder

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
            details=details
        )
        
        logger.info(f"Scene generated successfully after {result['iterations']} iterations")
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
    
    b = sb.exec("manim", "render", "-ql", "/data/scene.py", "-o", "/data/output.mp4")
    print(b.stdout.read())
    print(b.stderr.read())
    
    print(sb.exec("ls", "-la", "/data").stdout.read())
    print(sb.exec("ls", "-la", "/data").stderr.read())

@app.function(image=ai_image)
def test_openai():
    print("Hello World OpenAI")

@app.local_entrypoint()
def main():
    logger.info("Starting main application")
    result = test_scene_builder.remote()
    logger.info("Scene generation completed")

