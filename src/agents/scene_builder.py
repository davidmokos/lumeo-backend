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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SceneState(TypedDict):
    """State for the scene builder graph."""
    description: str  # Short description of what we're learning
    voiceover: str   # Current slide/scene voiceover text
    details: str     # Detailed description of the slide
    scene_code: str  # Generated Manim scene code
    output: str      # Output from scene execution
    error: str       # Any error messages
    iterations: int  # Number of attempts to generate/fix scene
    output_path: str  # Path where the output video should be saved

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
        model: str = "gpt-4",
    ):
        self.sandbox = sandbox
        self.model = model
        
    def _create_sandbox(self) -> modal.Sandbox:
        """Creates a Modal sandbox with Manim dependencies."""
        raise NotImplementedError("Sandbox should be passed to constructor")

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
        
        template = """
        You are a Manim expert tasked with creating a visual scene for a learning concept.
        
        Topic Description: {description}
        Voiceover Text: {voiceover}
        Detailed Description: {details}
        
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
        5. We're using Manim 0.18.1 - ShowCreation is obsolete, use Create function instead
        6. Don't use triple quotes for generated code, use single quotes instead
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["description", "voiceover", "details", "previous_error", "iterations", "previous_scene_code"]
        )
        
        previous_error = state.get("error", "")
        iterations = state.get("iterations", 0)
        
        logger.info(f"Generating with previous error: {previous_error}")
        
        chain = prompt | llm_with_tool | parser
        
        scene = chain.invoke({
            "description": state["description"],
            "voiceover": state["voiceover"],
            "details": state["details"],
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
        with self.sandbox.open("/data/scene.py", "w") as f:
            f.write(state["scene_code"])
        
        # Get output path from state
        output_path = state.get("output_path", "/data/output.mp4")
        
        # Execute scene
        result = self.sandbox.exec(
            "manim",
            "render",
            "-ql",  # medium quality, faster render
            "/data/scene.py",
            "-o",
            output_path
        )
        
        output = result.stdout.read()
        error = result.stderr.read()
        
        logger.info(f"Execution completed with error: {'None' if not error else 'Yes'}")
        if error:
            logger.error(f"Execution error: {error}")
        
        return {
            **state,
            "output": output,
            "error": error if error else "None",
            "output_path": output_path
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
            "scene_code": state["scene_code"],
            "output_path": state["output_path"],
            "iterations": state["iterations"]
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
        description: str,
        voiceover: str,
        details: str,
        output_path: str = "/data/output.mp4"
    ) -> Dict[str, Any]:
        """
        Generates a Manim scene based on the provided learning content.
        
        Args:
            description: Short description of what we're learning
            voiceover: Current slide/scene voiceover text
            details: Detailed description of the slide
            output_path: Path where the output video should be saved (default: /data/output.mp4)
            
        Returns:
            Dict containing the final scene code and output video path
        """
        logger.info(f"Starting scene generation with output path: {output_path}")
        graph = self.build_graph()
        runnable = graph.compile()
        
        result = runnable.invoke({
            "description": description,
            "voiceover": voiceover,
            "details": details,
            "scene_code": "",
            "output": "",
            "error": "",
            "iterations": 0,
            "output_path": output_path
        })
        
        logger.info(f"Scene generation completed after {result['iterations']} iterations")
        return result

