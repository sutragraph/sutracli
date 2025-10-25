from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional

from baml_client.types import Agent


class IndexingRequirement(Enum):
    """Indexing requirements that can be used as prerequisites."""

    INDEXING = auto()
    INCREMENTAL_INDEXING = auto()
    CROSS_INDEXING = auto()
    INCREMENTAL_CROSS_INDEXING = auto()


@dataclass
class AgentConfig:
    """Configuration for an agent node in the graph"""

    description: str
    prerequisites: List[IndexingRequirement]
    downstream: Optional[Agent]
    upstream: Optional[Agent]


class AgentGraph:
    """Static graph defining agent routing - pure map, no state"""

    GRAPH: Dict[Agent, AgentConfig] = {
        Agent.Roadmap: AgentConfig(
            description="",
            prerequisites=[
                IndexingRequirement.INDEXING,
                IndexingRequirement.INCREMENTAL_INDEXING,
                IndexingRequirement.CROSS_INDEXING,
                IndexingRequirement.INCREMENTAL_CROSS_INDEXING,
            ],
            downstream=Agent.Developer,
            upstream=None,
        ),
        Agent.Developer: AgentConfig(
            description="",
            prerequisites=[
                IndexingRequirement.INDEXING,
                IndexingRequirement.INCREMENTAL_INDEXING,
            ],
            downstream=Agent.QAEngineer,
            upstream=Agent.Roadmap,
        ),
        Agent.QAEngineer: AgentConfig(
            description="",
            prerequisites=[
                IndexingRequirement.INDEXING,
                IndexingRequirement.INCREMENTAL_INDEXING,
            ],
            downstream=None,
            upstream=Agent.Developer,
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
    def get_prerequisites(cls, agent_type: Agent) -> List[IndexingRequirement]:
        """Get list of prerequisite agents"""
        config = cls.get_config(agent_type)
        return config.prerequisites if config else []

    @classmethod
    def get_description(cls, agent_type: Agent) -> str:
        """Get description of agent"""
        config = cls.get_config(agent_type)
        return config.description if config else ""
