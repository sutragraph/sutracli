"""
Roadmap Agent - Strategic code change specialist

This agent provides precise roadmap-level modification instructions,
identifying specific functions, methods, and code blocks that need changes
without providing implementation details.
"""

from typing import List

from agents.agent_roadmap.prompts.agent_config import AGENT_CONFIG
from agents.agent_roadmap.prompts.project_context import PROJECT_CONTEXT
from agents.agent_roadmap.prompts.workflow import WORKFLOW
from agents.agent_roadmap.prompts.constraints import CONSTRAINTS
from agents.agent_roadmap.tool_list import TOOL_LIST


def get_base_system_prompt() -> str:
    """Get the complete system prompt for the Roadmap Agent."""
    from agents.shared.sutra_memory import SUTRA_MEMORY
    from agents.shared.system_info import SYSTEM_INFO
    from tools import get_tool_prompt, ToolName

    # Build tools section
    tools_section = "## AVAILABLE TOOLS\n\n"
    for tool_name in TOOL_LIST:
        tool_enum = ToolName(tool_name)
        tool_prompt = get_tool_prompt(tool_enum)
        tools_section += f"{tool_prompt}\n\n"

    # Combine all sections in logical order
    complete_prompt = f"""{AGENT_CONFIG}
    
{PROJECT_CONTEXT}

{tools_section}

{SUTRA_MEMORY}

{WORKFLOW}

{CONSTRAINTS}

{SYSTEM_INFO}

===="""

    return complete_prompt


def get_tools() -> List[str]:
    """Get list of available tools for this agent."""
    return TOOL_LIST


__all__ = [
    "get_base_system_prompt",
    "get_tools",
]
