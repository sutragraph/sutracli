from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from baml_client.types import Agent

if TYPE_CHECKING:
    from src.agent_management.agents.base import BaseAgent


class AgentRegistry:
    """Registry to hold agent instances - separate from routing"""

    _instances: Dict[Tuple[Agent, Path], "BaseAgent"] = {}

    @classmethod
    def _make_key(cls, agent_type: Agent, project_path: Path) -> Tuple[Agent, Path]:
        """Create composite key for agent registry"""
        return (agent_type, project_path.resolve())

    @classmethod
    def register(cls, agent: "BaseAgent") -> None:
        if agent.project_path is None:
            raise ValueError(
                f"Cannot register agent {agent.agent_type.name} without project_path"
            )
        key = cls._make_key(agent.agent_type, agent.project_path)
        cls._instances[key] = agent

    @classmethod
    def get(cls, agent_type: Agent, project_path: Path) -> Optional["BaseAgent"]:
        key = cls._make_key(agent_type, project_path)
        return cls._instances.get(key)

    @classmethod
    def get_by_agent(cls, agent: "BaseAgent") -> Optional["BaseAgent"]:
        if agent.project_path is None:
            return None
        return cls.get(agent.agent_type, agent.project_path)
