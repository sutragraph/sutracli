from typing import Any, Dict, Iterator

from models.agent import AgentAction

from .action import execute_completion_action as base_execute_completion_action


def execute_completion_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute qaengineer completion"""
    yield from base_execute_completion_action(action)
