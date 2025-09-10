"""
List Files Tool

Provides file listing functionality.
"""

from .action import execute_list_files_action


def get_action():
    """Get the list files action function."""
    return execute_list_files_action


__all__ = ["get_action"]
