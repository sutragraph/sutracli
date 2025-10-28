from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional

from baml_client.types import Agent


class IndexingRequirement(Enum):
    INDEXING = auto()
    MULTI_PROJECT_INCREMENTAL_INDEXING = auto()
    INCREMENTAL_INDEXING = auto()
    CROSS_INDEXING = auto()
    INCREMENTAL_CROSS_INDEXING = auto()


@dataclass
class AgentConfig:
    description: str
    prerequisites: List[IndexingRequirement]
    downstream: Optional[Agent]
    upstream: Optional[Agent]
    module: Optional[str] = None
    class_name: Optional[str] = None


class AgentGraph:
    GRAPH: Dict[Agent, AgentConfig] = {
        Agent.Roadmap: AgentConfig(
            description="",
            prerequisites=[
                IndexingRequirement.INDEXING,
                IndexingRequirement.MULTI_PROJECT_INCREMENTAL_INDEXING,
                IndexingRequirement.CROSS_INDEXING,
                IndexingRequirement.INCREMENTAL_CROSS_INDEXING,
            ],
            downstream=Agent.Developer,
            upstream=None,
            module="agent_management.agents.roadmap",
            class_name="RoadmapAgent",
        ),
        Agent.Developer: AgentConfig(
            description="",
            prerequisites=[
                IndexingRequirement.INDEXING,
                IndexingRequirement.INCREMENTAL_INDEXING,
            ],
            downstream=Agent.QAEngineer,
            upstream=Agent.Roadmap,
            module="agent_management.agents.developer",
            class_name="DeveloperAgent",
        ),
        Agent.QAEngineer: AgentConfig(
            description="",
            prerequisites=[
                IndexingRequirement.INDEXING,
                IndexingRequirement.INCREMENTAL_INDEXING,
            ],
            downstream=None,
            upstream=Agent.Developer,
            module="agent_management.agents.qa_engineer",
            class_name="QAEngineerAgent",
        ),
    }

    @classmethod
    def get_all_agents(cls) -> List[Agent]:
        return list(cls.GRAPH.keys())

    @classmethod
    def get_config(cls, agent_type: Agent) -> Optional[AgentConfig]:
        return cls.GRAPH.get(agent_type)

    @classmethod
    def get_downstream(cls, agent_type: Agent) -> Optional[Agent]:
        config = cls.get_config(agent_type)
        return config.downstream if config else None

    @classmethod
    def get_upstream(cls, agent_type: Agent) -> Optional[Agent]:
        config = cls.get_config(agent_type)
        return config.upstream if config else None

    @classmethod
    def get_prerequisites(cls, agent_type: Agent) -> List[IndexingRequirement]:
        config = cls.get_config(agent_type)
        return config.prerequisites if config else []

    @classmethod
    def get_description(cls, agent_type: Agent) -> str:
        config = cls.get_config(agent_type)
        return config.description if config else ""
