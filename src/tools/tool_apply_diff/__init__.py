"""
Apply Diff Tool

Provides functionality for applying code diffs and patches to files.
"""

from .action import execute_apply_diff_action
from .prompt import APPLY_DIFF_TOOL


def get_action():
    """Get the apply diff action function."""
    return execute_apply_diff_action


def get_prompt():
    """Get the apply diff tool prompt."""
    return APPLY_DIFF_TOOL


__all__ = ["get_action", "get_prompt"]
