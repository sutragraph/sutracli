"""
Unified agent execution system using BAMLService.

This module provides a single interface to execute different types of agents
using the existing BAMLService infrastructure.
"""

# Re-export BAML types for convenience
from baml_client.types import (
    Agent,
    BaseCompletionParams,
    ProjectContext,
    RoadmapAgentParams,
    RoadmapCompletionParams,
    RoadmapResponse,
)

from .executor import AgentResponse, execute_agent
from .utils.project_context import get_project_context_for_agent

__all__ = [
    # Agent execution functions
    "execute_agent",
    # Utility functions
    "get_project_context_for_agent",
    # Types (re-exported from BAML client)
    "Agent",
    "AgentResponse",
    "ProjectContext",
    "RoadmapAgentParams",
    "RoadmapResponse",
    "RoadmapCompletionParams",
    "BaseCompletionParams",
]
