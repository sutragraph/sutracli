"""
Semantic Search Tool

Provides semantic search functionality.
"""

from .action import execute_semantic_search_action


def get_action():
    """Get the semantic search action function."""
    return execute_semantic_search_action


__all__ = ["get_action"]
