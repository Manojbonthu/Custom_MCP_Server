import json
import logging
from typing import Optional, Dict, Any, Tuple, Protocol, List
from .state import StepInfo

logger = logging.getLogger(__name__)

class LLMClientProtocol(Protocol):
    def generate_json(self, prompt: str) -> dict:
        """Returns a parsed JSON dictionary from the LLM"""
        ...

class DecisionEngine:
    def __init__(self, llm_client: LLMClientProtocol, available_tools: List[Dict[str, Any]]):
        self.llm_client = llm_client
        self.available_tools = available_tools

    def choose_capability(self, step: StepInfo) -> Optional[Tuple[str, Dict[str, Any]]]:
        # Format the tools for the prompt so the LLM knows what is available
        tools_list = "\n".join([f"- {t.get('name')}: {t.get('description')}" for t in self.available_tools])
        
        prompt = f"""
You are an AI decision engine routing tasks to tools.
Available tools:
{tools_list}

Select the SINGLE best tool to accomplish the following task.
Extract any necessary arguments from the task description.
If no tool fits, return tool_name as "null".
Return ONLY valid JSON in the following format:
{{
    "tool_name": "the_tool",
    "arguments": {{"arg1": "value1"}}
}}

Task description: {step.description}
"""
        try:
            response = self.llm_client.generate_json(prompt)
            tool_name = response.get("tool_name")
            tool_args = response.get("arguments", {})
            
            if not tool_name or tool_name == "null":
                logger.warning(f"LLM determined no tool could fulfill: {step.description}")
                return None
                
            return tool_name, tool_args
            
        except Exception as e:
            logger.error(f"Failed to choose capability dynamically: {e}")
            return None
