"""
Prerequisites management for agents.
"""

from .agent_config import AgentConfig, AgentRegistry, get_agent_registry

__all__ = [
    "AgentConfig",
    "AgentRegistry",
    "get_agent_registry",
]
