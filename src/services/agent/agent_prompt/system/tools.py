"""
Tool integration for system prompts.
Provides access to all available tools for the agent.
"""

from tools import get_tool_prompt, AVAILABLE_TOOLS
from utils.system_utils import get_current_directory


def get_all_tools() -> str:
    """Get all tool prompts formatted for the system prompt."""
    current_dir = get_current_directory()
    
    tool_prompts = []
    
    for tool_name in AVAILABLE_TOOLS:
        try:
            prompt = get_tool_prompt(tool_name)
            # Format prompts that need current directory
            if hasattr(prompt, 'format') and '{current_dir}' in prompt:
                formatted_prompt = prompt.format(current_dir=current_dir)
            else:
                formatted_prompt = prompt
            tool_prompts.append(formatted_prompt)
        except Exception as e:
            # Skip tools that fail to load
            continue
    
    return f"""# Tools

{chr(10).join(tool_prompts)}"""


__all__ = ["get_all_tools"]
