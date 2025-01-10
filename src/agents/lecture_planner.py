import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.utils.function_calling import convert_to_openai_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Slide(BaseModel):
    """Structure for a single slide in the lecture."""
    voiceover: str = Field(description="The text that will be played on this slide")
    description: str = Field(description="Detailed description of what scenebuilder agent should generate on the slide using manim library")

class LecturePlan(BaseModel):
    """Complete lecture plan with multiple slides."""
    title: str = Field(description="Title of the lecture")
    slides: List[Slide] = Field(description="List of slides in the lecture")

class LecturePlanner:
    """Agent that plans lectures by breaking down topics into slides."""
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        
    def plan_lecture(self, topic: str, resources: str = "") -> LecturePlan:
        """
        Plans a lecture by breaking down a topic into a sequence of slides.
        
        Args:
            topic: The main topic or concept to teach
            resources: Optional additional resources or context
            
        Returns:
            LecturePlan containing the sequence of slides
        """
        logger.info(f"Planning lecture for topic: {topic}")
        
        llm = ChatOpenAI(
            # temperature=0.7,  # Some creativity in planning
            model=self.model,
        )
        
        lecture_tool = convert_to_openai_tool(LecturePlan)
        llm_with_tool = llm.bind(
            tools=[lecture_tool],
            tool_choice={"type": "function", "function": {"name": "LecturePlan"}}
        )
        parser = PydanticToolsParser(tools=[LecturePlan])
        
        template = """
        You are an expert educator tasked with planning a comprehensive lecture on a topic.
        The lecture should be engaging, clear, and well-structured, progressing from basic concepts to more advanced details.
        
        Topic: {topic}
        Additional Resources/Context: {resources}
        
        Create a lecture plan with approximately 5-7 slides that:
        1. Starts with an engaging introduction
        2. Progresses logically from basic to advanced concepts
        3. Includes clear visualizations that support learning
        4. Maintains student engagement throughout
        5. Ends with a strong conclusion or practical application
        
        For each slide:
        1. Write clear, conversational voiceover text (15-30 seconds when spoken)
        2. Provide detailed description for the Manim visualization, including:
           - What elements should appear
           - How they should be animated
           - How the visuals support the voiceover
           - Don't use any code in the description
           
        Remember:
        - Keep visualizations simple and focused
        - Ensure voiceover and visuals are synchronized
        - Use animations to reveal information gradually
        - Make complex concepts tangible through metaphors and examples
        - Total lecture length should be around 2-3 minutes
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["topic", "resources"]
        )
        
        chain = prompt | llm_with_tool | parser
        
        result = chain.invoke({
            "topic": topic,
            "resources": resources
        })
        
        lecture_plan = result[0]
        logger.info(f"Generated lecture plan with {len(lecture_plan.slides)} slides")
        
        return lecture_plan
