from typing import Iterator, Dict, Any
from models.agent import AgentAction


def execute_completion_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute generic completion tool - handles BaseCompletionParams only."""

    try:
        params = action.parameters
        result = params.get("result", "Task completed")

        yield {
            "simple":True,
            "type": "tool_use",
            "tool_name": "attempt_completion",
            "data": {"result": result}
        }

    except Exception as e:
        yield {
            "type": "tool_error",
            "tool_name": "attempt_completion",
            "error": str(e)
        }
