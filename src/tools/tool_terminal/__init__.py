"""
Terminal Commands Tool

Provides terminal command execution functionality.
"""

from .action import execute_terminal_action
from .prompt import TERMINAL_COMMANDS_TOOL


def get_action():
    """Get the terminal commands action function."""
    return execute_terminal_action


def get_prompt():
    """Get the terminal commands tool prompt."""
    return TERMINAL_COMMANDS_TOOL


__all__ = ["get_action", "get_prompt"]
