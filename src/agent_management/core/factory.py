from importlib import import_module
from pathlib import Path
from typing import Type

from baml_client.types import Agent

from .agent_graph import AgentGraph


class AgentFactory:
    @staticmethod
    def _get_agent_class(agent_type: Agent) -> Type:
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

    @staticmethod
    def get_or_create(agent_type: Agent, project_path: Path):
        from .registry import AgentRegistry

        existing = AgentRegistry.get(agent_type, project_path)
        if existing is not None:
            return existing

        cls = AgentFactory._get_agent_class(agent_type)
        return cls(project_path=project_path)
