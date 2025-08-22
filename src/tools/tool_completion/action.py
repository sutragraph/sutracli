from typing import Iterator, Dict, Any
import time
from models.agent import AgentAction

def execute_completion_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute completion tool."""
    
    # Handle both dict and string formats for parameters
    if isinstance(action.parameters, dict):
        result = action.parameters.get("result", "Task completed")
    elif isinstance(action.parameters, str):
        result = action.parameters
    else:
        result = "Task completed"

    yield {
        "type": "completion",
        "tool_name": "attempt_completion",
        "result": result,
        "success": True,
        "timestamp": time.time(),
    }
