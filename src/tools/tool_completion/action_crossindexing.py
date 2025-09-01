from typing import Iterator, Dict, Any
from models.agent import AgentAction
from .action import execute_completion_action as base_execute_completion_action


def execute_completion_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute roadmap completion with union type detection."""
    try:
        yield from base_execute_completion_action(action)

    except Exception as e:
        yield {
            "type": "tool_error",
            "tool_name": "attempt_completion",
            "error": str(e)
        }
