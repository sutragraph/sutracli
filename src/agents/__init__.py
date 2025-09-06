"""
Agents module - Contains all agent configurations with their prompts and system configurations.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
import importlib
from agents.shared import (
    get_project_context_for_agent,
    inject_project_context
)


class AgentName(Enum):
    ROADMAP = "agent_roadmap"


# Default agent configuration - all features disabled by default
DEFAULT_AGENT_CONFIG = {
    "requires_project_context": False,
    # Add other config options here as needed
}

def get_agent_config(agent_name: AgentName) -> Dict[str, Any]:
    """Get configuration for a specific agent, with defaults applied."""
    config = DEFAULT_AGENT_CONFIG.copy()
    try:
        # Import the agent's module and get its config
        agent_module = importlib.import_module(f"agents.{agent_name.value}")
        if hasattr(agent_module, "CONFIG"):
            config.update(agent_module.CONFIG)
    except ImportError:
        # If agent module doesn't exist or has issues, use defaults
        pass
    return config


def agent_requires_project_context(agent_name: AgentName) -> bool:
    """Check if an agent requires project context injection."""
    config = get_agent_config(agent_name)
    return config.get("requires_project_context", False)


def get_agent_system_prompt(agent_name: AgentName, query: Optional[str] = None) -> str:
    """Get complete system prompt for the agent using new structure."""
    try:
        # Import the agent's module and get its system prompt
        agent_module = importlib.import_module(f"agents.{agent_name.value}")
        if not hasattr(agent_module, "get_base_system_prompt"):
            raise AttributeError(
                f"Agent '{agent_name.value}' missing 'get_base_system_prompt' function"
            )

        # Get base system prompt dictionary
        prompt_dict = agent_module.get_base_system_prompt()

        # Check if agent requires project context and query is provided
        if query and agent_requires_project_context(agent_name):
            project_context = get_project_context_for_agent(agent_name, query)
            if project_context:
                prompt_dict = inject_project_context(prompt_dict, project_context)

        # Assemble final prompt string from dictionary
        if hasattr(agent_module, "assemble_prompt_from_dict"):
            return agent_module.assemble_prompt_from_dict(prompt_dict)
        else:
            # Fallback for agents that don't have assemble function
            raise AttributeError(f"Agent '{agent_name.value}' missing 'assemble_prompt_from_dict' function")

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
    "get_agent_config",
    "agent_requires_project_context",
    "AVAILABLE_AGENTS",
    "DEFAULT_AGENT_CONFIG",
]
