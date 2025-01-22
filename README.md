# Lumeo Backend - AI-Powered Lecture Generation

Lumeo's backend service powers automated lecture generation using [Manim](https://www.manim.community/) and [Claude](https://www.anthropic.com/claude) AI. Special thanks to [3Blue1Brown](https://www.3blue1brown.com/) (Grant Sanderson) for creating Manim and inspiring this project.

## Project Overview

Lumeo consists of two main components:
- **Frontend** ([lumeo-frontend](https://github.com/davidmokos/lumeo-frontend)): A Next.js web application providing the user interface
- **Backend** (this repository): A Python service using LangGraph agents to generate Manim scenes and orchestrate the video creation process

## Architecture

The backend is built with:
- **[Modal](https://modal.com/)**: For serverless deployment and execution
- **[LangGraph](https://python.langchain.com/docs/langgraph)**: For AI agent orchestration
- **[Manim](https://www.manim.community/)**: For mathematical animation generation
- **[Claude](https://www.anthropic.com/claude)**: For AI-powered scene generation
- **[FFmpeg](https://ffmpeg.org/)**: For video processing and merging

## Getting Started

### Prerequisites

1. Python 3.11+
2. [Modal](https://modal.com/) account
3. [Anthropic API key](https://www.anthropic.com/product) for Claude
4. [FFmpeg](https://ffmpeg.org/) for video processing

### Installation

1. Clone the repository:
```bash
git clone https://github.com/davidmokos/lumeo-backend.git
cd lumeo-backend
```

2. Install Modal CLI:
```bash
pip install modal
```

3. Set up Modal:
```bash
modal setup
```

4. Add environment variables to Modal dashboard.

### Development

For local testing:
```bash
modal serve main.py
```

### Deployment

To deploy to Modal's cloud:
```bash
modal deploy main.py
```

## Key Components

- **Scene Builder**: AI agent that generates Manim scenes based on lecture content
- **Lecture Planner**: Structures lecture content into coherent scenes
- **Video Processing**: Handles video generation, merging, and post-processing
- **Storage**: Manages video and asset storage

## Learn More

- [Modal Documentation](https://modal.com/docs)
- [Manim Community](https://www.manim.community/)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [Claude API Documentation](https://docs.anthropic.com/claude/docs)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
