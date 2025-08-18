"""
Agents module - Contains all agent configurations with their prompts and system configurations.
"""

from enum import Enum
from typing import Dict, List
from functools import lru_cache
import importlib
from pathlib import Path


class AgentName(Enum):
    ROADMAP = "agent_roadmap"


@lru_cache(maxsize=None)
def _import_agent_module(agent_name: AgentName, module_name: str):
    """Import and cache agent module."""
    try:
        return importlib.import_module(
            f"agents.{agent_name.value}.prompts.{module_name}"
        )
    except ImportError as e:
        raise ImportError(
            f"Failed to import agent '{agent_name.value}' module '{module_name}': {e}"
        )


def get_agent_identity(agent_name: AgentName) -> str:
    """Get agent identity prompt."""
    module = _import_agent_module(agent_name, "identity")
    if not hasattr(module, "IDENTITY"):
        raise AttributeError(
            f"Agent '{agent_name.value}' missing 'IDENTITY' in identity.py"
        )
    return module.IDENTITY

def get_agent_tool_usage_cases(agent_name: AgentName) -> str:
    """Get agent tool usage cases prompt."""
    module = _import_agent_module(agent_name, "tool_use_cases")
    if not hasattr(module, "TOOL_USAGE_CASES"):
        raise AttributeError(
            f"Agent '{agent_name.value}' missing 'TOOL_USAGE_CASES' in tool_usage_examples.py"
        )
    return module.TOOL_USAGE_CASES

def get_agent_objective(agent_name: AgentName) -> str:
    """Get agent objective prompt."""
    module = _import_agent_module(agent_name, "objective")
    if not hasattr(module, "OBJECTIVE"):
        raise AttributeError(
            f"Agent '{agent_name.value}' missing 'OBJECTIVE' in objective.py"
        )
    return module.OBJECTIVE


def get_agent_capabilities(agent_name: AgentName) -> str:
    """Get agent capabilities prompt."""
    module = _import_agent_module(agent_name, "capabilities")
    if not hasattr(module, "CAPABILITIES"):
        raise AttributeError(
            f"Agent '{agent_name.value}' missing 'CAPABILITIES' in capabilities.py"
        )
    return module.CAPABILITIES


def get_agent_rules(agent_name: AgentName) -> str:
    """Get agent rules prompt."""
    module = _import_agent_module(agent_name, "rules")
    if not hasattr(module, "RULES"):
        raise AttributeError(f"Agent '{agent_name.value}' missing 'RULES' in rules.py")
    return module.RULES


def get_agent_guidelines(agent_name: AgentName) -> str:
    """Get agent guidelines prompt (required)."""
    module = _import_agent_module(agent_name, "guidelines")
    if not hasattr(module, "GUIDELINES"):
        raise AttributeError(
            f"Agent '{agent_name.value}' missing 'GUIDELINES' in guidelines.py"
        )
    return module.GUIDELINES


def get_agent_tools(agent_name: AgentName) -> List[str]:
    """Get agent tool list."""
    try:
        module = importlib.import_module(f"agents.{agent_name.value}.tool_list")
    except ImportError as e:
        raise ImportError(f"Failed to import agent '{agent_name.value}' tool_list: {e}")

    if not hasattr(module, "TOOL_LIST"):
        raise AttributeError(
            f"Agent '{agent_name.value}' missing 'TOOL_LIST' in tool_list.py"
        )
    return module.TOOL_LIST


def get_agent_system_prompt(agent_name: AgentName) -> str:
    """Get complete system prompt for the agent."""
    from agents.shared.sutra_memory import SUTRA_MEMORY
    from agents.shared.workspace_structure import WORKSPACE_STRUCTURE
    from agents.shared.system_info import SYSTEM_INFO
    from tools import get_tool_prompt, ToolName

    # Get all agent-specific prompts
    identity = get_agent_identity(agent_name)
    objective = get_agent_objective(agent_name)
    capabilities = get_agent_capabilities(agent_name)
    rules = get_agent_rules(agent_name)
    guidelines = get_agent_guidelines(agent_name)
    tool_names = get_agent_tools(agent_name)
    tool_usage_cases = get_agent_tool_usage_cases(agent_name)

    # Get actual tool prompts using the existing get_tool_prompt function
    tools_section = "## AVAILABLE TOOLS\n\n"

    for tool_name in tool_names:
        tool_enum = ToolName(tool_name)
        tool_prompt = get_tool_prompt(tool_enum)
        print("adding tool prompt:", tool_name)  # Debugging line
        tools_section += f"{tool_prompt}\n\n"

    # Combine all sections
    complete_prompt = f"""{identity}

{tools_section}

{SUTRA_MEMORY}

{objective}

{capabilities}

{guidelines}

{tool_usage_cases}

{rules}

{SYSTEM_INFO}

{WORKSPACE_STRUCTURE}

===="""

    return complete_prompt


def get_base_system_prompt(agent_name: AgentName) -> str:
    """Get the base system prompt for the agent (alias for get_agent_system_prompt)."""
    return get_agent_system_prompt(agent_name)


AVAILABLE_AGENTS = list(AgentName)

__all__ = [
    "AgentName",
    "get_agent_system_prompt",
    "get_base_system_prompt",
    "get_agent_identity",
    "get_agent_objective",
    "get_agent_capabilities",
    "get_agent_rules",
    "get_agent_tools",
    "AVAILABLE_AGENTS",
]
