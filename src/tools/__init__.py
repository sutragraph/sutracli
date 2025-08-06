"""
Tools module - Contains all agent tools with their actions and prompts.
"""

from enum import Enum
from typing import Callable, Dict, Iterator, Any
from functools import lru_cache
import importlib
from models.agent import AgentAction

ToolActionFunction = Callable[[AgentAction], Iterator[Dict[str, Any]]]

class ToolName(Enum):
    SEMANTIC_SEARCH = "tool_semantic_search"
    APPLY_DIFF = "tool_apply_diff"
    COMPLETION = "tool_completion"
    DATABASE_SEARCH = "tool_database_search"
    LIST_FILES = "tool_list_files"
    SEARCH_KEYWORD = "tool_search_keyword"
    TERMINAL_COMMANDS = "tool_terminal_commands"
    WEB_SCRAP = "tool_web_scrap"
    WEB_SEARCH = "tool_web_search"
    WRITE_TO_FILE = "tool_write_to_file"


@lru_cache(maxsize=None)
def _import_tool_module(tool_name: ToolName):
    """Import and cache tool module."""
    try:
        return importlib.import_module(f"tools.{tool_name.value}")
    except ImportError as e:
        raise ImportError(f"Failed to import tool '{tool_name.value}': {e}")


def get_tool_action(tool_name: ToolName) -> ToolActionFunction:
    """Get tool action function."""
    module = _import_tool_module(tool_name)
    if not hasattr(module, 'get_action'):
        raise AttributeError(f"Tool '{tool_name.value}' missing 'get_action' function")
    return module.get_action()


def get_tool_prompt(tool_name: ToolName) -> str:
    """Get tool prompt."""
    module = _import_tool_module(tool_name)
    if not hasattr(module, 'get_prompt'):
        raise AttributeError(f"Tool '{tool_name.value}' missing 'get_prompt' function")
    return module.get_prompt()


# Legacy name mapping for backward compatibility
TOOL_NAME_MAPPING = {
    "semantic_search": ToolName.SEMANTIC_SEARCH,
    "database": ToolName.DATABASE_SEARCH,
    "execute_command": ToolName.TERMINAL_COMMANDS,
    "apply_diff": ToolName.APPLY_DIFF,
    "write_to_file": ToolName.WRITE_TO_FILE,
    "list_files": ToolName.LIST_FILES,
    "search_keyword": ToolName.SEARCH_KEYWORD,
    "attempt_completion": ToolName.COMPLETION,
    "web_scrap": ToolName.WEB_SCRAP,
    "web_search": ToolName.WEB_SEARCH,
}

AVAILABLE_TOOLS = list(ToolName)

# Import ActionExecutor after all functions are defined to avoid circular imports
from .executor import ActionExecutor

__all__ = ["ToolName", "get_tool_action", "get_tool_prompt", "AVAILABLE_TOOLS", "TOOL_NAME_MAPPING", "ActionExecutor"]