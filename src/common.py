import modal

ai_image = (
    modal.Image.debian_slim(python_version="3.11")
    # .pip_install("modal>=0.71.0",
    # "openai>=1.12.0",
    # "langgraph>=0.2.39",
    # "langchain>=0.1.9",
    # "langchain-core>=0.1.27",
    # "langchain-openai>=0.0.8",
    # "langchain-community>=0.0.24",
    # "pydantic>=2.6.1",
    # "python-dotenv>=1.0.1",
    # "typing-extensions>=4.9.0")
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
    modal.Secret.from_name("openai-secret", required_keys=["OPENAI_API_KEY"]),
    modal.Secret.from_name("langsmith-secret", required_keys=["LANGCHAIN_API_KEY"]),
    modal.Secret.from_name("elevenlabs-secret", required_keys=["ELEVENLABS_API_KEY"]),
]

volumes = {
    "/data": modal.Volume.from_name("learn-anything-vol", create_if_missing=True)
}
