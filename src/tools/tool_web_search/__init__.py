"""
Web Search Tool

Provides web search functionality.
"""

from .action import execute_web_search_action
from .prompt import WEB_SEARCH_TOOL

def get_action():
    """Get the web search action function."""
    return execute_web_search_action

def get_prompt():
    """Get the web search tool prompt."""
    return WEB_SEARCH_TOOL

__all__ = ["get_action", "get_prompt"]
