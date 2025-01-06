import os
import modal

app = modal.App(name="learn-anything")
sandbox_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("build-essential", "python3-dev", "libcairo2-dev", "libpango1.0-dev", "ffmpeg", "python3-pip", "texlive", "texlive-latex-extra")
    .pip_install("manim")
)

vol = modal.Volume.from_name("learn-anything-vol", create_if_missing=True)

ai_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("openai")
    .pip_install("langgraph")
    .pip_install("langchain-openai")
    .pip_install("langchain-anthropic")
)


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

