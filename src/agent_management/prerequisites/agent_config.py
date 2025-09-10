#!/usr/bin/env python3
"""
Agent Configuration System for SutraKit.
Provides modular configuration for different agents and their requirements.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

# Import Agent enum
from src.agents_new import Agent


@dataclass
class AgentConfig:
    """Configuration for a SutraKit agent."""
    key: Agent
    name: str
    description: str
    requires_indexing: bool = False
    requires_cross_indexing: bool = False
    config_file: Optional[str] = None

class AgentRegistry:
    """Registry for managing available agents."""

    def __init__(self):
        """Initialize the agent registry with default agents."""
        self._agents: Dict[Agent, AgentConfig] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        """Register the default agents."""
        # Roadmap Agent
        self.register_agent(
            AgentConfig(
                key=Agent.ROADMAP,
                name="Roadmap Agent",
                description="Analyzes codebase structure and creates comprehensive development roadmaps",
                requires_indexing=True,
                requires_cross_indexing=True,
            )
        )


    def register_agent(self, agent: AgentConfig):
        """Register a new agent."""
        self._agents[agent.key] = agent

    def get_agent(self, key: Agent) -> Optional[AgentConfig]:
        """Get an agent by enum. Returns None if agent is not registered."""
        return self._agents.get(key)

    def get_available_agents(self) -> List[AgentConfig]:
        """Get agents that are currently available (implemented)."""
        return list(self._agents.values())


# Global agent registry instance
_agent_registry = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry
