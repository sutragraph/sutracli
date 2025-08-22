"""
Write To File Tool

File writing operations.
"""

from .action import execute_write_to_file_action
from .prompt import WRITE_TO_FILE_TOOL

def get_action():
    """Get the write_to_file action function."""
    return execute_write_to_file_action

def get_prompt():
    """Get the write_to_file tool prompt."""
    return WRITE_TO_FILE_TOOL

__all__ = ["get_action", "get_prompt"]
