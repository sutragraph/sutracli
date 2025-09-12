"""
Tools module - Contains all agent tools with their actions and prompts.
"""

import importlib
from functools import lru_cache
from typing import Any, Callable, Dict, Iterator

from loguru import logger

from baml_client.types import Agent
from models.agent import AgentAction

ToolActionFunction = Callable[[AgentAction], Iterator[Dict[str, Any]]]


@lru_cache(maxsize=None)
def _import_tool_module(tool_name: str):
    """Import and cache tool module."""
    try:
        return importlib.import_module(f"tools.tool_{tool_name}")
    except ImportError as e:
        raise ImportError(f"Failed to import tool '{tool_name}': {e}")


def get_completion_action(agent: Agent) -> ToolActionFunction:
    """Factory function to get agent-specific completion action."""
    try:
        # Try to import agent-specific completion module
        agent_module_name = f"tool_completion.action_{agent.value.lower()}"
        module = importlib.import_module(f"tools.{agent_module_name}")
        if hasattr(module, "execute_completion_action"):
            return module.execute_completion_action
    except ImportError:
        # Fall back to default completion action
        logger.warning(f"Failed to import agent-specific completion module for {agent}")
        pass

    # Default completion action
    logger.warning(f"Using default completion action for {agent}")
    from .tool_completion.action import execute_completion_action

    return execute_completion_action


def get_tool_action(agent: Agent, tool_name: str) -> ToolActionFunction:
    """Get tool action function with special handling for completion."""
    # Special handling for completion tool - use factory
    if tool_name == "attempt_completion":
        return get_completion_action(agent)

    # Regular tool handling
    module = _import_tool_module(tool_name)
    if not hasattr(module, "get_action"):
        raise AttributeError(f"Tool '{tool_name}' missing 'get_action' function")
    return module.get_action()
