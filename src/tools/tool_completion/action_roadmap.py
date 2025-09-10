from typing import Any, Dict, Iterator

from baml_client.types import Agent
from models.agent import AgentAction

from .action import execute_completion_action as base_execute_completion_action


def execute_completion_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute roadmap completion with union type detection."""

    try:
        params = action.parameters

        # Union type detection: RoadmapCompletionParams | BaseCompletionParams
        if isinstance(params, dict):
            if "projects" in params and "summary" in params:
                yield from _handle_roadmap_completion(params)
            elif "result" in params:
                yield from base_execute_completion_action(action)
            else:
                # Invalid parameters
                yield {
                    "type": "tool_error",
                    "tool_name": "attempt_completion",
                    "error": f"Invalid completion parameters. Expected either 'result' or 'projects+summary', got: {list(params.keys())}",
                }
        else:
            yield from base_execute_completion_action(action)

    except Exception as e:
        yield {"type": "tool_error", "tool_name": "attempt_completion", "error": str(e)}


def _handle_roadmap_completion(params: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle complex roadmap completion with projects and summary."""
    projects = params.get("projects", [])
    summary = params.get("summary", "")

    # Return structured response for build_tool_status to handle display
    yield {
        "type": "tool_use",
        "tool_name": "attempt_completion",
        "agent_name": Agent.ROADMAP,
        "data": {"summary": summary, "projects": projects},
    }
