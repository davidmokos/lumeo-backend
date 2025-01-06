import os
import modal
from src.common import sandbox_image, ai_image

app = modal.App(name="learn-anything")
vol = modal.Volume.from_name("learn-anything-vol", create_if_missing=True)


@app.function(volumes={"/data": vol})
def test_manim():
    print("Hello World Manim")
    sb = modal.Sandbox.create(app=app, image=sandbox_image, volumes={"/data": vol})
    # print(os.getcwd())
    # print(os.listdir())
    
    with sb.open("/data/scene.py", "w") as f:
        f.write("""from manim import *
class CreateCircle(Scene):
    def construct(self):
        circle = Circle()
        circle.set_fill(PINK, opacity=0.5)
        self.play(Create(circle))""")
    
    # print(sb.exec("pwd").stdout.read())
    # print(sb.exec("ls", "-la").stdout.read())
    
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
    test_manim.remote()

