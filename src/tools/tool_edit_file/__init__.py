"""
Edit File Tool

Provides functionality for applying code diffs and patches to files.
"""

from .action import execute_edit_file_action


def get_action():
    """Get the edit file action function."""
    return execute_edit_file_action


__all__ = ["get_action"]
