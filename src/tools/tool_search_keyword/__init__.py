"""
Search Keyword Tool

Provides keyword search functionality.
"""

from .action import execute_search_keyword_action
from .prompt import SEARCH_KEYWORD_TOOL

def get_action():
    """Get the search keyword action function."""
    return execute_search_keyword_action

def get_prompt():
    """Get the search keyword tool prompt."""
    return SEARCH_KEYWORD_TOOL

__all__ = ["get_action", "get_prompt"]
