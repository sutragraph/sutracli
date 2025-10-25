from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set

from agent_management.core.agent_graph import AgentGraph
from agent_management.core.registry import AgentRegistry
from baml_client.types import Agent
from services.agent.memory_management import SutraMemoryManager
from services.agent.memory_management.models import MemorySection
from services.agent_service_new import AgentService
from tools import AllToolParams


@dataclass
class AgentData:
    context: str


class BaseAgent(ABC):
    def __init__(self, agent_type: Agent, project_path: Optional[Path] = None):
        self.agent_type = agent_type
        self.memory = SutraMemoryManager()
        self.project_path = project_path
        if project_path:
            AgentRegistry.register(self)

    @abstractmethod
    def from_upstream(self, data: AgentData) -> None:
        pass

    @abstractmethod
    def from_downstream(self, data: AgentData) -> None:
        pass

    def send_to_downstream(self, data: AgentData) -> None:
        if not self.project_path:
            raise ValueError(f"Project path must be set for {self.agent_type.name}")

        downstream_type = AgentGraph.get_downstream(self.agent_type)

        if downstream_type:
            downstream = AgentRegistry.get(downstream_type, self.project_path)
            if downstream:
                print(f"[{self.agent_type.name}] → [{downstream_type.name}]")
                downstream.from_upstream(data)
        else:
            print(f"[{self.agent_type.name}] End of flow")

    def send_to_upstream(self, data: AgentData) -> None:
        if not self.project_path:
            raise ValueError(f"Project path must be set for {self.agent_type.name}")

        upstream_type = AgentGraph.get_upstream(self.agent_type)

        if upstream_type:
            upstream = AgentRegistry.get(upstream_type, self.project_path)
            if upstream:
                print(f"[{self.agent_type.name}] ← [{upstream_type.name}]")
                upstream.from_downstream(data)
        else:
            print(f"[{self.agent_type.name}] No upstream agent")

    def run_agent_loop(self, problem_query: str) -> Optional[AllToolParams]:
        if not self.project_path:
            raise ValueError(f"Project path must be set for {self.agent_type.name}")

        agent_service = AgentService(
            agent_name=self.agent_type,
            project_path=self.project_path,
            sutra_memory=self.memory,
        )
        return agent_service.solve_problem(problem_query)

    def load_memory_from_agent(
        self,
        agent_type: Agent,
        preserve_sections: Optional[Set[MemorySection]] = None,
        project_path: Optional[Path] = None,
    ) -> bool:
        target_path = project_path or self.project_path
        if not target_path:
            raise ValueError(
                f"Project path must be set or provided for {self.agent_type.name}"
            )

        source_agent = AgentRegistry.get(agent_type, target_path)
        if not source_agent:
            return False

        if preserve_sections:
            filtered_state = source_agent.memory.filter_sections(preserve_sections)
            return self.memory.import_memory_state(filtered_state)

        source_state = source_agent.memory.export_memory_state()
        return self.memory.import_memory_state(source_state)

    def copy_memory_from_agent(
        self,
        agent_type: Agent,
        sections_to_copy: Optional[Set[MemorySection]] = None,
        project_path: Optional[Path] = None,
    ) -> bool:
        target_path = project_path or self.project_path
        if not target_path:
            raise ValueError(
                f"Project path must be set or provided for {self.agent_type.name}"
            )

        source_agent = AgentRegistry.get(agent_type, target_path)
        if not source_agent:
            return False

        if sections_to_copy:
            filtered_state = source_agent.memory.filter_sections(sections_to_copy)
            return self.memory.import_memory_state(filtered_state)

        source_state = source_agent.memory.export_memory_state()
        return self.memory.import_memory_state(source_state)

    def clear_memory_sections(self, sections: Set[MemorySection]) -> None:
        self.memory.clear_sections(sections)
