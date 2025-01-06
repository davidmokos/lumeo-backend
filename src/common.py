import modal

ai_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
)

sandbox_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("build-essential", "python3-dev", "libcairo2-dev", "libpango1.0-dev", "ffmpeg", "python3-pip", "texlive", "texlive-latex-extra")
    .pip_install("manim")
)

secrets = [
    modal.Secret.from_name(
        "openai-secret", required_keys=["OPENAI_API_KEY"]
    ),
],

