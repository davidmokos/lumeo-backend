from langgraph.graph import StateGraph
from typing import TypedDict, Dict, Any
import modal
from pydantic import BaseModel, Field
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.utils.function_calling import convert_to_openai_tool
import os
import logging
from langsmith import Client as LangsmithClient

from src.database.scene_repository import SceneRepository
from src.database.storage import StorageBucket, StorageClient
from src.schema.lecture import Lecture
from src.schema.scene import Scene, SceneStatus
from src.services.voiceover_service import embed_audio_and_subtitles, embed_audio_and_subtitles_new, generate_audio, generate_subtitles
from src.common import read, vol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SceneState(TypedDict):
    """State for the scene builder graph."""
    lecture_topic: str  # Short description of what we're learning
    scene_voiceover: str   # Current slide/scene voiceover text
    scene_description: str     # Detailed description of the slide
    scene_code: str  # Generated Manim scene code
    output: str      # Output from scene execution
    error: str       # Any error messages
    iterations: int  # Number of attempts to generate/fix scene
    scene_id: str  # ID of the scene

class Decision(str, Enum):
    """Possible decisions after evaluating scene generation."""
    FINISH = "finish"
    RETRY = "retry"

class SceneCode(BaseModel):
    """Generated scene code structure."""
    explanation: str = Field(description="Explanation of how the scene visualizes the concept")
    imports: str = Field(description="Import statements for the scene")
    scene_code: str = Field(description="The actual Manim scene code")
    scene_name: str = Field(description="Name of the Manim scene class")

class SceneEvaluation(BaseModel):
    """Evaluation of scene execution."""
    explanation: str = Field(description="Explanation for the decision")
    decision: Decision = Field(description="Decision to finish or retry")

class SceneBuilder:
    """Agent that builds Manim scenes based on learning content descriptions."""
    
    def __init__(
        self,
        sandbox: modal.Sandbox,
        model: str = "gpt-4o",
    ):
        self.sandbox = sandbox
        self.model = model
        
    def build_graph(self) -> StateGraph:
        """Builds the LangGraph for scene generation."""
        graph = StateGraph(SceneState)
        
        # Add nodes
        graph.add_node("generate", self._generate_scene)
        graph.add_node("execute", self._execute_scene)
        graph.add_node("evaluate", self._evaluate_execution)
        graph.add_node("finish", self._finish)
        
        # Add edges
        graph.add_edge("generate", "execute")
        graph.add_conditional_edges(
            "execute",
            self._should_retry,
            {
                "generate": "generate",
                "evaluate": "evaluate"
            }
        )
        graph.add_conditional_edges(
            "evaluate",
            self._should_finish,
            {
                "finish": "finish",
                "generate": "generate"
            }
        )
        
        # Set entry and finish points
        graph.set_entry_point("generate")
        graph.set_finish_point("finish")
        
        return graph

    def _generate_scene(self, state: SceneState) -> SceneState:
        """Generates Manim scene code based on the learning content description."""
        logger.info(f"Generating scene, iteration {state.get('iterations', 0) + 1}")
        
        llm = ChatOpenAI(
            temperature=0, 
            model=self.model,
        )
        scene_tool = convert_to_openai_tool(SceneCode)
        llm_with_tool = llm.bind(
            tools=[scene_tool],
            tool_choice={"type": "function", "function": {"name": "SceneCode"}}
        )
        parser = PydanticToolsParser(tools=[SceneCode])
        
        template = """You are a Manim expert tasked with creating a visual scene for a learning concept.

Topic Description: {lecture_topic}
Voiceover Text: {scene_voiceover}
Detailed Description: {scene_description}

Create a Manim scene that effectively visualizes this concept.
The scene should be engaging, clear, and match the voiceover timing.

Previous Iterations: {iterations}
Previous Scene Code: {previous_scene_code}
Previous Error: {previous_error}

Important:
1. Keep animations simple and focused
2. Ensure all objects are properly initialized
3. Use basic shapes and transformations
4. Follow Manim best practices for scene construction
5. Don't use ShowCreation, always use Create instead
6. Don't use triple quotes for generated code, use single quotes instead

# Essential Manim Scene Patterns

from manim import *

# 1. Basic Scene with Animation
class BasicScene(Scene):
    def construct(self):
        # Create objects
        circle = Circle(radius=1, color=BLUE)
        square = Square(color=RED)
        
        # Basic animations
        self.play(Create(circle))
        self.play(Transform(circle, square))
        self.wait()

# 2. Mathematical Equations
class MathScene(Scene):
    def construct(self):
        # LaTeX equations
        equation = MathTex(r"\sum_{{n=1}}^\infty \frac{{1}}{{n^2}} = \frac{{\pi^2}}{{6}}")
        text = Tex(r"This is \LaTeX")
        
        VGroup(text, equation).arrange(DOWN)
        self.play(Write(text), FadeIn(equation))

# 3. Coordinate System and Graphs
class GraphScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            tips=False
        )
        
        # Plot function
        graph = axes.plot(lambda x: np.sin(x), color=BLUE)
        self.add(axes, graph)

# 4. Moving Objects with Updaters
class UpdaterScene(Scene):
    def construct(self):
        dot = Dot()
        line = Line(ORIGIN, RIGHT * 3)
        
        # Add updater to dot
        dot.add_updater(lambda d: d.move_to(line.get_start()))
        self.add(dot, line)
        self.play(line.animate.shift(UP * 2))

# 5. 3D Scene
class ThreeDScene(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        sphere = Surface(
            lambda u, v: np.array([
                np.cos(u) * np.cos(v),
                np.cos(u) * np.sin(v),
                np.sin(u)
            ]),
            v_range=[0, TAU],
            u_range=[-PI/2, PI/2]
        )
        
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
        self.add(axes, sphere)

# 6. Value Tracker for Animations
class ValueTrackerScene(Scene):
    def construct(self):
        tracker = ValueTracker(0)
        
        # Create object that depends on tracker
        dot = Dot().add_updater(
            lambda d: d.set_x(tracker.get_value())
        )
        
        self.add(dot)
        self.play(tracker.animate.set_value(5))

# 7. Geometric Transformations
class TransformScene(Scene):
    def construct(self):
        circle = Circle()
        square = Square()
        
        self.play(
            circle.animate.scale(2).set_color(RED),
            rate_func=smooth
        )
        self.play(
            circle.animate.apply_function(
                lambda p: p + np.array([np.sin(p[1]), np.cos(p[0]), 0])
            )
        )

# Common Animation Patterns:
# 1. Creation: Create(), Write(), FadeIn()
# 2. Transformation: Transform(), ReplacementTransform()
# 3. Movement: .animate.shift(), .animate.move_to(), MoveAlongPath()
# 4. Fading: FadeOut(), FadeIn()
# 5. Updating: add_updater(), remove_updater()

# Common Properties:
# - Color: set_color(), set_fill(), set_stroke()
# - Position: move_to(), shift(), next_to()
# - Size: scale(), stretch()
# - Grouping: VGroup(), Group()"""
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["lecture_topic", "scene_voiceover", "scene_description", "previous_error", "iterations", "previous_scene_code"]
        )
        
        previous_error = state.get("error", "")
        iterations = state.get("iterations", 0)
        
        # logger.info(f"Generating with previous error: {previous_error}")
        
        chain = prompt | llm_with_tool | parser
        
        scene = chain.invoke({
            "lecture_topic": state["lecture_topic"],
            "scene_voiceover": state["scene_voiceover"],
            "scene_description": state["scene_description"],
            "previous_error": previous_error,
            "iterations": iterations,
            "previous_scene_code": state["scene_code"]
        })
        
        scene_code = f"{scene[0].imports}\n\n{scene[0].scene_code}"
        logger.info(f"Generated scene code with name: {scene[0].scene_name}")
        
        return {
            **state,
            "scene_code": scene_code,
            "iterations": iterations + 1
        }

    def _execute_scene(self, state: SceneState) -> SceneState:
        """Executes the generated Manim scene in the sandbox."""
        logger.info(f"Executing scene, iteration {state['iterations']}")
        
        # Write scene to file
        scene_file_path = f"/data/scene_{state['scene_id']}.py"
        with self.sandbox.open(scene_file_path, "w") as f:
            f.write(state["scene_code"])
        
        # Get output path from state
        scene_output_path = f"/data/scene_{state['scene_id']}.mp4"
        
        # Execute scene
        result = self.sandbox.exec(
            "manim",
            "render",
            "-ql",  # medium quality, faster render
            scene_file_path,
            "-o",
            scene_output_path
        )
        
        vol.commit()
        
        # Safely read stdout and stderr with error handling
        
        output = read(result.stdout)
        error = read(result.stderr)
        
        return {
            **state,
            "output": output,
            "error": error if error else "None",
        }

    def _evaluate_execution(self, state: SceneState) -> SceneState:
        """Evaluates the scene execution results."""
        logger.info(f"Evaluating execution, iteration {state['iterations']}")
        
        llm = ChatOpenAI(
            temperature=0, 
            model=self.model,
        )
        eval_tool = convert_to_openai_tool(SceneEvaluation)
        llm_with_tool = llm.bind(
            tools=[eval_tool],
            tool_choice={"type": "function", "function": {"name": "SceneEvaluation"}}
        )
        parser = PydanticToolsParser(tools=[SceneEvaluation])
        
        template = """
        Evaluate the execution of this Manim scene:
        
        Scene Code:
        {scene_code}
        
        Output:
        {output}
        
        StdErr Output:
        {error}
        
        Current Iteration: {iterations}
        Maximum Iterations: 5
        
        Decide whether to finish or retry. Consider:
        1. Technical success (no errors)
        2. Scene effectiveness (visualizes the concept well)
        3. Current iteration (we must finish at iteration 5)
        4. Scene complexity and feasibility
        
        If we're at iteration 5, you MUST choose to finish regardless of the result.
        If retrying on earlier iterations, be specific about what needs to be fixed.
        
        Remember:
        - A simple scene that works is better than a complex scene that fails
        - We have limited iterations to get it right
        - Focus on basic shapes and animations that are most likely to work
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["scene_code", "output", "error", "iterations"]
        )
        
        chain = prompt | llm_with_tool | parser
        
        evaluation = chain.invoke({
            "scene_code": state["scene_code"],
            "output": state["output"],
            "error": state["error"],
            "iterations": state["iterations"]
        })
        
        logger.info(f"Evaluation decision: {evaluation[0].decision}")
        logger.info(f"Evaluation explanation: {evaluation[0].explanation}")
        
        return {
            **state,
            "evaluation": evaluation[0]
        }

    def _finish(self, state: SceneState) -> Dict[str, Any]:
        """Finalizes the scene generation process."""
        return {
            **state
        }

    def _should_retry(self, state: SceneState) -> str:
        """Decides whether to retry scene generation based on execution results."""
        iterations = state.get("iterations", 0)
        has_error = not "File ready at" in state["output"] 
        
        logger.info(f"Checking retry condition - iterations: {iterations}, has_error: {has_error}")
        
        # If we've hit max iterations, go to evaluate even if there's an error
        if iterations >= 5:
            logger.info("Max iterations reached, forcing evaluation")
            return "evaluate"
            
        # If there's an error and we haven't hit max iterations, retry
        if has_error:
            logger.info("Error detected, retrying generation")
            return "generate"
            
        # No error, proceed to evaluation
        logger.info("No error, proceeding to evaluation")
        return "evaluate"

    def _should_finish(self, state: SceneState) -> str:
        """Decides whether to finish or retry based on evaluation."""
        iterations = state.get("iterations", 0)
        decision = state["evaluation"].decision
        
        logger.info(f"Checking finish condition - iterations: {iterations}, decision: {decision}")
        
        # Always finish if we've hit max iterations
        if iterations >= 5:
            logger.info("Max iterations reached, forcing finish")
            return "finish"
            
        # Finish if the evaluation says it's good
        if decision == Decision.FINISH:
            logger.info("Evaluation indicates success, finishing")
            return "finish"
            
        # Otherwise retry if we haven't hit max iterations
        logger.info("Evaluation indicates retry needed")
        return "generate"

    def generate_scene(
        self,
        lecture: Lecture,
        scene: Scene
    ) -> Scene:
        
        logger.info(f"Starting scene generation")
        graph = self.build_graph()
        runnable = graph.compile()
        
        result = runnable.invoke({
            "lecture_topic": lecture.topic,
            "scene_voiceover": scene.voiceover,
            "scene_description": scene.description,
            "scene_code": "",
            "output": "",
            "error": "",
            "iterations": 0,
            "scene_id": scene.id
        })
        
        vol.commit()
        vol.reload()
        
        scene_repository = SceneRepository()
        scene_video_path = f"/data/scene_{scene.id}.mp4"
        
        # if video does not exist, create an empty video as fallback
        if not os.path.exists(scene_video_path):
            logger.info(f"Scene {scene.id} video not generated, creating empty video as fallback")
            from src.services.voiceover_service import create_empty_video
            create_empty_video(scene_video_path)
        
        scene_audio_path = f"/data/scene_{scene.id}.mp3"
        scene_subtitles_path = f"/data/scene_{scene.id}.vtt"
        full_video_path = f"/data/scene_{scene.id}_full.mp4"
        
        vol.commit()
        vol.reload()
        generate_audio(voiceover_text=scene.voiceover, output_path=scene_audio_path)
        vol.commit()
        vol.reload()
        generate_subtitles(audio_path=scene_audio_path, vtt_file_path=scene_subtitles_path)
        vol.commit()
        vol.reload()
        
        embed_audio_and_subtitles_new(
            # sandbox=self.sandbox,
            video_path=scene_video_path,
            audio_path=scene_audio_path,
            vtt_file_path=scene_subtitles_path,
            output_path=full_video_path
        )
        
        storage_client = StorageClient()
        video_url = storage_client.upload_file(
            bucket=StorageBucket.SCENES,
            file_path=full_video_path,
            destination_path=f"{scene.id}/video.mp4"
        )
        
        
        new_scene = scene_repository.update(scene.id, {
            "status": SceneStatus.COMPLETED,
            "code": result["scene_code"],
            "video_url": video_url
        })
        
        vol.commit()
        
        logger.info(f"Scene generation completed")
        return new_scene
    
