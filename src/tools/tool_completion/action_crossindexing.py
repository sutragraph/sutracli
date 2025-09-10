from typing import Iterator, Dict, Any
from models.agent import AgentAction
from .action import execute_completion_action as base_execute_completion_action


def execute_completion_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute roadmap completion with union type detection."""
    yield from base_execute_completion_action(action)
