import os
import modal
from src.common import sandbox_image, ai_image, secrets
from src.scene_builder import SceneBuilder

app = modal.App(name="learn-anything")
vol = modal.Volume.from_name("learn-anything-vol", create_if_missing=True)

@app.function(image=ai_image, volumes={"/data": vol}, secrets=secrets)
def test_scene_builder():
    """Test the SceneBuilder agent with a simple concept."""
    builder = SceneBuilder(app=app, volume=vol)
    
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
    """
    
    result = builder.generate_scene(
        description=description,
        voiceover=voiceover,
        details=details
    )
    
    print(f"Scene generated after {result['iterations']} iterations")
    print(f"Output video saved to: {result['output_path']}")
    print("\nGenerated Scene Code:")
    print(result['scene_code'])

@app.function(volumes={"/data": vol})
def test_manim():
    print("Hello World Manim")
    sb = modal.Sandbox.create(app=app, image=sandbox_image, volumes={"/data": vol})
    
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
    # print("Hello World")
    # test_openai.remote()
    test_scene_builder.remote()

