
from .common import sandbox_image, ai_image
from langgraph.graph import StateGraph
from typing import TypedDict, Dict, Any
import modal
from pydantic import BaseModel, Field
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.utils.function_calling import convert_to_openai_tool


class SceneState(TypedDict):
    """State for the scene builder graph."""
    description: str  # Short description of what we're learning
    voiceover: str   # Current slide/scene voiceover text
    details: str     # Detailed description of the slide
    scene_code: str  # Generated Manim scene code
    output: str      # Output from scene execution
    error: str       # Any error messages
    iterations: int  # Number of attempts to generate/fix scene

class Decision(str, Enum):
    """Possible decisions after evaluating scene generation."""
    FINISH = "finish"
    RETRY = "retry"

class SceneCode(BaseModel):
    """Generated scene code structure."""
    scene_name: str = Field(description="Name of the Manim scene class")
    imports: str = Field(description="Import statements for the scene")
    scene_code: str = Field(description="The actual Manim scene code")
    explanation: str = Field(description="Explanation of how the scene visualizes the concept")

class SceneEvaluation(BaseModel):
    """Evaluation of scene execution."""
    decision: Decision = Field(description="Decision to finish or retry")
    explanation: str = Field(description="Explanation for the decision")

class SceneBuilder:
    """Agent that builds Manim scenes based on learning content descriptions."""
    
    def __init__(
        self,
        app: modal.App,
        volume: modal.Volume,
        model: str = "gpt-4",
        debug: bool = False
    ):
        self.app = app
        self.volume = volume
        self.model = model
        self.debug = debug
        self.sandbox = self._create_sandbox()
        
    def _create_sandbox(self) -> modal.Sandbox:
        """Creates a Modal sandbox with Manim dependencies."""
        
        return modal.Sandbox.create(
            image=sandbox_image,
            app=self.app,
            volumes={"/data": self.volume}
        )

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
        llm = ChatOpenAI(temperature=0, model=self.model)
        scene_tool = convert_to_openai_tool(SceneCode)
        llm_with_tool = llm.bind(
            tools=[scene_tool],
            tool_choice={"type": "function", "function": {"name": "SceneCode"}}
        )
        parser = PydanticToolsParser(tools=[SceneCode])
        
        template = """
        You are a Manim expert tasked with creating a visual scene for a learning concept.
        
        Topic Description: {description}
        Voiceover Text: {voiceover}
        Detailed Description: {details}
        
        Create a Manim scene that effectively visualizes this concept.
        The scene should be engaging, clear, and match the voiceover timing.
        
        {previous_error}
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["description", "voiceover", "details", "previous_error"]
        )
        
        previous_error = f"\nPrevious Error: {state['error']}" if state.get("error") else ""
        
        chain = prompt | llm_with_tool | parser
        
        scene = chain.invoke({
            "description": state["description"],
            "voiceover": state["voiceover"],
            "details": state["details"],
            "previous_error": previous_error
        })
        
        scene_code = f"{scene[0].imports}\n\n{scene[0].scene_code}"
        
        return {
            **state,
            "scene_code": scene_code,
            "iterations": state.get("iterations", 0) + 1
        }

    def _execute_scene(self, state: SceneState) -> SceneState:
        """Executes the generated Manim scene in the sandbox."""
        # Write scene to file
        with self.sandbox.open("/data/scene.py", "w") as f:
            f.write(state["scene_code"])
        
        # Execute scene
        result = self.sandbox.exec(
            "manim",
            "render",
            "-ql",  # medium quality, faster render
            "/data/scene.py",
            "-o",
            "/data/output.mp4"
        )
        
        output = result.stdout.read()
        error = result.stderr.read()
        
        return {
            **state,
            "output": output,
            "error": error if error else "None"
        }

    def _evaluate_execution(self, state: SceneState) -> SceneState:
        """Evaluates the scene execution results."""
        llm = ChatOpenAI(temperature=0, model=self.model)
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
        
        Error:
        {error}
        
        Decide whether to finish (if successful) or retry (if there were errors).
        Consider both technical success and whether the scene effectively visualizes the concept.
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["scene_code", "output", "error"]
        )
        
        chain = prompt | llm_with_tool | parser
        
        evaluation = chain.invoke({
            "scene_code": state["scene_code"],
            "output": state["output"],
            "error": state["error"]
        })
        
        return {
            **state,
            "evaluation": evaluation[0]
        }

    def _finish(self, state: SceneState) -> Dict[str, Any]:
        """Finalizes the scene generation process."""
        return {
            "scene_code": state["scene_code"],
            "output_path": "/data/output.mp4",
            "iterations": state["iterations"]
        }

    def _should_retry(self, state: SceneState) -> str:
        """Decides whether to retry scene generation based on execution results."""
        return "generate" if state["error"] != "None" else "evaluate"

    def _should_finish(self, state: SceneState) -> str:
        """Decides whether to finish or retry based on evaluation."""
        if state["evaluation"].decision == Decision.FINISH or state["iterations"] >= 3:
            return "finish"
        return "generate"

    def generate_scene(
        self,
        description: str,
        voiceover: str,
        details: str
    ) -> Dict[str, Any]:
        """
        Generates a Manim scene based on the provided learning content.
        
        Args:
            description: Short description of what we're learning
            voiceover: Current slide/scene voiceover text
            details: Detailed description of the slide
            
        Returns:
            Dict containing the final scene code and output video path
        """
        graph = self.build_graph()
        runnable = graph.compile()
        
        result = runnable.invoke({
            "description": description,
            "voiceover": voiceover,
            "details": details,
            "scene_code": "",
            "output": "",
            "error": "",
            "iterations": 0
        })
        
        return result

