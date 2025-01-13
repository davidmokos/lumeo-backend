from typing import cast
import modal
from modal.io_streams import StreamReader

ai_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install_from_requirements("requirements.txt")
    .env({"LANGCHAIN_TRACING_V2": "true"})
    .env({"LANGCHAIN_ENDPOINT": "https://api.smith.langchain.com"})
    .env({"LANGCHAIN_PROJECT": "projectlearn"})
)

sandbox_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("build-essential", "python3-dev", "libcairo2-dev", "libpango1.0-dev", "ffmpeg", "python3-pip", "texlive", "texlive-latex-extra")
    .pip_install("manim")
)

secrets = [
    modal.Secret.from_name(
        "projectlearn-secret",
        required_keys=[
            "OPENAI_API_KEY",
            "LANGCHAIN_API_KEY",
            "ELEVENLABS_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ]
    ),
]

vol = modal.Volume.from_name("learn-anything-vol", create_if_missing=True)

volumes = {
    "/data": vol
}



def read(stream: StreamReader):
    """Fetch the entire contents of the stream until EOF.

    **Usage**

    ```python
    from modal import Sandbox

    sandbox = Sandbox.create("echo", "hello", app=app)
    sandbox.wait()

    print(sandbox.stdout.read())
    ```
    """
    data_str = ""
    for message in stream._get_logs():
        if message is None:
            break
        data_str += message.decode("utf-8", errors="replace")

    return data_str