#!/usr/bin/env python3
"""
Agent Configuration System for SutraKit.
Provides modular configuration for different agents and their requirements.
"""

import os
import subprocess
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentPrerequisite:
    """Represents a prerequisite for an agent."""
    name: str
    description: str
    required: bool = True
    check_function: Optional[str] = None


@dataclass
class AgentConfig:
    """Configuration for a SutraKit agent."""
    key: str
    name: str
    description: str
    requires_indexing: bool = False
    requires_cross_indexing: bool = False
    config_file: Optional[str] = None

class AgentRegistry:
    """Registry for managing available agents."""

    def __init__(self):
        """Initialize the agent registry with default agents."""
        self._agents: Dict[str, AgentConfig] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        """Register the default agents."""
        # Roadmap Agent
        self.register_agent(
            AgentConfig(
                key="roadmap",
                name="Roadmap Agent",
                description="Analyzes codebase structure and creates comprehensive development roadmaps",
                requires_indexing=True,
                requires_cross_indexing=True,
            )
        )

    def register_agent(self, agent: AgentConfig):
        """Register a new agent."""
        self._agents[agent.key] = agent

    def get_agent(self, key: str) -> Optional[AgentConfig]:
        """Get an agent by key."""
        return self._agents.get(key)

    def list_agents(self) -> List[AgentConfig]:
        """Get all registered agents."""
        return list(self._agents.values())

    def get_available_agents(self) -> List[AgentConfig]:
        """Get agents that are currently available (implemented)."""
        # For now, only roadmap agent is implemented
        implemented_agents = ["roadmap"]
        return [agent for agent in self._agents.values() if agent.key in implemented_agents]

class AgentPrerequisiteChecker:
    """Checks prerequisites for agents."""

    @staticmethod
    def check_llm_provider() -> bool:
        """Check if LLM provider is configured."""
        try:
            from config.settings import get_config
            config = get_config()
            return hasattr(config, 'llm') and config.llm is not None
        except Exception:
            return False

    @staticmethod
    def check_project_directory() -> bool:
        """Check if current directory is accessible."""
        try:
            current_dir = Path.cwd()
            return current_dir.exists() and current_dir.is_dir()
        except Exception:
            return False

    @staticmethod
    def check_database_permissions() -> bool:
        """Check if database directory is writable."""
        try:
            from config.settings import get_config
            config = get_config()
            db_dir = Path(config.storage.data_dir).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            return db_dir.exists() and os.access(db_dir, os.W_OK)
        except Exception:
            return False

    @staticmethod
    def check_static_analysis_tools() -> bool:
        """Check if static analysis tools are available (optional)."""
        tools = ['pylint', 'flake8', 'mypy', 'bandit']
        available_tools = []

        for tool in tools:
            try:
                subprocess.run([tool, '--version'],
                             capture_output=True,
                             check=True,
                             timeout=5)
                available_tools.append(tool)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return len(available_tools) > 0

    def check_prerequisite(self, prerequisite: AgentPrerequisite) -> bool:
        """Check a specific prerequisite."""
        if not prerequisite.check_function:
            return True  # No check function means it's always satisfied

        check_method = getattr(self, prerequisite.check_function, None)
        if not check_method:
            return True  # Unknown check function, assume satisfied

        try:
            return check_method()
        except Exception:
            return False

    def check_agent_prerequisites(self, agent: AgentConfig) -> Dict[str, bool]:
        """Check all prerequisites for an agent."""
        results = {}
        for prereq in agent.prerequisites:
            results[prereq.name] = self.check_prerequisite(prereq)
        return results


# Global agent registry instance
_agent_registry = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry


def get_agent_checker() -> AgentPrerequisiteChecker:
    """Get an agent prerequisite checker instance."""
    return AgentPrerequisiteChecker()
