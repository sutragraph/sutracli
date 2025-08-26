"""
Shared agents module - Contains utilities and services shared across agents.
"""

from .project_context import (
    get_project_context_for_agent,
    inject_project_context,
    get_project_context_for_query
)

__all__ = [
    "get_project_context_for_agent",
    "inject_project_context",
    "get_project_context_for_query"
]
