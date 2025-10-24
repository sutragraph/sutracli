from typing import TYPE_CHECKING, Dict, Optional

from baml_client.types import Agent

if TYPE_CHECKING:
    from .base import BaseAgent


class AgentRegistry:
    """Registry to hold agent instances - separate from routing"""

    _instances: Dict[Agent, "BaseAgent"] = {}

    @classmethod
    def register(cls, agent: "BaseAgent") -> None:
        """Register an agent instance"""
        cls._instances[agent.agent_type] = agent

    @classmethod
    def get(cls, agent_type: Agent) -> Optional["BaseAgent"]:
        """Get registered agent instance"""
        return cls._instances.get(agent_type)
