"""
Diagnostics Tool

Provides functionality for applying code diffs and patches to files.
"""

from .action import execute_diagnostics_action


def get_action():
    """Get the diagnostics action function."""
    return execute_diagnostics_action


__all__ = ["get_action"]
