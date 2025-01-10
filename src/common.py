import modal

ai_image = (
    modal.Image.debian_slim(python_version="3.11")
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

volumes = {
    "/data": modal.Volume.from_name("learn-anything-vol", create_if_missing=True)
}
