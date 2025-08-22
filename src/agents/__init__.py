"""
Agents module - Contains all agent configurations with their prompts and system configurations.
"""

from enum import Enum
from typing import List
import importlib


class AgentName(Enum):
    ROADMAP = "agent_roadmap"


def get_agent_system_prompt(agent_name: AgentName) -> str:
    """Get complete system prompt for the agent using new structure."""
    try:
        # Import the agent's module and get its system prompt
        agent_module = importlib.import_module(f"agents.{agent_name.value}")
        if not hasattr(agent_module, "get_base_system_prompt"):
            raise AttributeError(
                f"Agent '{agent_name.value}' missing 'get_base_system_prompt' function"
            )
        return agent_module.get_base_system_prompt()
    except ImportError as e:
        raise ImportError(f"Failed to import agent '{agent_name.value}': {e}")


def get_agent_tools(agent_name: AgentName) -> List[str]:
    """Get agent tool list using new structure."""
    try:
        # Import the agent's module and get its tools
        agent_module = importlib.import_module(f"agents.{agent_name.value}")
        if not hasattr(agent_module, "get_tools"):
            raise AttributeError(
                f"Agent '{agent_name.value}' missing 'get_tools' function"
            )
        return agent_module.get_tools()
    except ImportError as e:
        raise ImportError(f"Failed to import agent '{agent_name.value}': {e}")


def get_base_system_prompt(agent_name: AgentName) -> str:
    """Get the base system prompt for the agent (alias for get_agent_system_prompt)."""
    return get_agent_system_prompt(agent_name)


AVAILABLE_AGENTS = list(AgentName)

__all__ = [
    "AgentName",
    "get_agent_system_prompt",
    "get_base_system_prompt",
    "get_agent_tools",
    "AVAILABLE_AGENTS",
]
