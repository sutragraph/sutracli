"""
Database Search Tool

Provides database search functionality.
"""

from .action import execute_database_search_action
from .prompt import DATABASE_SEARCH_TOOL

def get_action():
    """Get the database search action function."""
    return execute_database_search_action

def get_prompt():
    """Get the database search tool prompt."""
    return DATABASE_SEARCH_TOOL

__all__ = ["get_action", "get_prompt"]
