"""
Roadmap Agent - Strategic code change specialist

This agent provides precise roadmap-level modification instructions,
identifying specific functions, methods, and code blocks that need changes
without providing implementation details.
"""

from typing import List, Dict, Any

from agents.agent_roadmap.prompts.agent_config import AGENT_CONFIG
from agents.agent_roadmap.prompts.workflow import WORKFLOW
from agents.agent_roadmap.prompts.constraints import CONSTRAINTS
from agents.agent_roadmap.tool_list import TOOL_LIST

# Agent configuration
CONFIG = {
    "requires_project_context": True,
}


def get_base_system_prompt() -> Dict[str, Any]:
    """
    Get the base system prompt structure for the Roadmap Agent.
    Returns a dictionary that can be assembled into the final prompt.
    """
    from agents.shared.sutra_memory import SUTRA_MEMORY
    from agents.shared.system_info import SYSTEM_INFO
    from tools import get_tool_prompt, ToolName

    # Build tools section
    tools_section = "## AVAILABLE TOOLS\n\n"
    for tool_name in TOOL_LIST:
        tool_enum = ToolName(tool_name)
        tool_prompt = get_tool_prompt(tool_enum)
        tools_section += f"{tool_prompt}\n\n"

    # Return structured prompt sections
    return {
        "agent_config": AGENT_CONFIG,
        "project_context": "",
        "tools_section": tools_section,
        "sutra_memory": SUTRA_MEMORY,
        "workflow": WORKFLOW,
        "constraints": CONSTRAINTS,
        "system_info": SYSTEM_INFO,
        "separator": "====="
    }


def get_tools() -> List[str]:
    """Get list of available tools for this agent."""
    return TOOL_LIST


def assemble_prompt_from_dict(prompt_dict: Dict[str, Any]) -> str:
    """
    Assemble the final prompt string from the prompt dictionary.

    Args:
        prompt_dict: Dictionary containing prompt sections

    Returns:
        Complete assembled prompt string
    """
    return f"""{prompt_dict['agent_config']}

{prompt_dict['project_context']}

{prompt_dict['tools_section']}

{prompt_dict['sutra_memory']}

{prompt_dict['workflow']}

{prompt_dict['constraints']}

{prompt_dict['system_info']}

{prompt_dict['separator']}"""


__all__ = [
    "get_base_system_prompt",
    "get_tools",
    "assemble_prompt_from_dict",
    "CONFIG",
]
