"""
Web Scrap Tool

Provides web scraping functionality.
"""

from .action import execute_web_scrap_action
from .prompt import WEB_SCRAP_TOOL

def get_action():
    """Get the web scrap action function."""
    return execute_web_scrap_action

def get_prompt():
    """Get the web scrap tool prompt."""
    return WEB_SCRAP_TOOL

__all__ = ["get_action", "get_prompt"]
