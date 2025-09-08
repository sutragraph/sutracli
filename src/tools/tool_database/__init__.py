"""
Database Search Tool

Provides database search functionality.
"""

from .action import execute_database_search_action


def get_action():
    """Get the database search action function."""
    return execute_database_search_action


__all__ = ["get_action"]
