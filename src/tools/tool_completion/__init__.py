"""
Completion Tool

Provides code completion functionality.
"""

from .action import execute_completion_action
from .prompt import COMPLETION_TOOL

def get_action():
    """Get the completion action function."""
    return execute_completion_action

def get_prompt():
    """Get the completion tool prompt."""
    return COMPLETION_TOOL

__all__ = ["get_action", "get_prompt"]
