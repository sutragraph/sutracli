"""
Semantic Search Tool

Provides semantic search functionality.
"""

from .action import execute_semantic_search_action
from .prompt import SEMANTIC_SEARCH_TOOL

def get_action():
    """Get the semantic search action function."""
    return execute_semantic_search_action

def get_prompt():
    """Get the semantic search tool prompt."""
    return SEMANTIC_SEARCH_TOOL

__all__ = ["get_action", "get_prompt"]
