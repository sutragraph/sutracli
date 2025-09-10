"""
Search Keyword Tool

Provides keyword search functionality.
"""

from .action import execute_search_keyword_action


def get_action():
    """Get the search keyword action function."""
    return execute_search_keyword_action


__all__ = ["get_action"]
