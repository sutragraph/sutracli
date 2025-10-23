from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from baml_client.types import Agent


@dataclass
class AgentConfig:
    """Configuration for an agent node in the graph"""

    prerequisites: List[Agent]
    downstream: Optional[Agent]
    upstream: Optional[Agent]


class AgentGraph:
    """Static graph defining agent routing - pure map, no state"""

    GRAPH: Dict[Agent, AgentConfig] = {
        Agent.ROADMAP: AgentConfig(
            prerequisites=[], downstream=Agent.Developer, upstream=None
        ),
        Agent.Developer: AgentConfig(
            prerequisites=[], downstream=Agent.QAEngineer, upstream=Agent.ROADMAP
        ),
        Agent.QAEngineer: AgentConfig(
            prerequisites=[], downstream=None, upstream=Agent.Developer
        ),
    }

    @classmethod
    def get_all_agents(cls) -> List[Agent]:
        """Get list of all agents in the graph"""
        return list(cls.GRAPH.keys())

    @classmethod
    def get_config(cls, agent_type: Agent) -> Optional[AgentConfig]:
        """Get complete configuration for an agent"""
        return cls.GRAPH.get(agent_type)

    @classmethod
    def get_downstream(cls, agent_type: Agent) -> Optional[Agent]:
        """Get downstream agent type"""
        config = cls.get_config(agent_type)
        return config.downstream if config else None

    @classmethod
    def get_upstream(cls, agent_type: Agent) -> Optional[Agent]:
        """Get upstream agent type"""
        config = cls.get_config(agent_type)
        return config.upstream if config else None

    @classmethod
    def get_prerequisites(cls, agent_type: Agent) -> List[Agent]:
        """Get list of prerequisite agents"""
        config = cls.get_config(agent_type)
        return config.prerequisites if config else []
