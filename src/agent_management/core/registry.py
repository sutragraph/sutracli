from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Type

from baml_client.types import Agent

from .agent_graph import AgentGraph

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

    @classmethod
    def _get_agent_class(cls, agent_type: Agent) -> Type:
        """Get the agent class for the given agent type."""
        cfg = AgentGraph.get_config(agent_type)
        if not cfg or not cfg.module or not cfg.class_name:
            raise ValueError(f"No implementation configured for {agent_type}")
        module = import_module(cfg.module)
        try:
            return getattr(module, cfg.class_name)
        except AttributeError as e:
            raise ValueError(
                f"Class {cfg.class_name} not found in module {cfg.module} for {agent_type}"
            ) from e

    @classmethod
    def get_or_create(cls, agent_type: Agent, project_path: Path) -> "BaseAgent":
        """Get an existing agent instance or create a new one."""
        existing = cls.get(agent_type, project_path)
        if existing is not None:
            return existing

        agent_class = cls._get_agent_class(agent_type)
        return agent_class(project_path=project_path)

    @classmethod
    def clear_all_instances(cls) -> None:
        """Clear all registered agent instances."""
        cls._instances.clear()
