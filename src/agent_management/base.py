from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set

from baml_client.types import Agent
from src.tools import AllToolParams

from ..services.agent.memory_management import SutraMemoryManager
from ..services.agent_service_new import AgentService
from .agent_graph import AgentGraph
from .registry import AgentRegistry


@dataclass
class AgentData:
    """Data structure for agent communication"""

    context: str


class BaseAgent(ABC):
    """Base class for all agents"""

    _memory_store = {}

    def __init__(self, agent_type: Agent, project_path: Optional[Path] = None):
        self.agent_type = agent_type
        self.memory = SutraMemoryManager()
        self._agent_instance_id = id(self)
        self.project_path = project_path
        AgentRegistry.register(self)

    @abstractmethod
    def from_upstream(self, data: AgentData) -> None:
        """Handle data from upstream agent"""
        pass

    @abstractmethod
    def from_downstream(self, data: AgentData) -> None:
        """Handle data from downstream agent"""
        pass

    def send_to_downstream(self, data: AgentData) -> None:
        """Send data to next agent in flow"""
        downstream_type = AgentGraph.get_downstream(self.agent_type)

        if downstream_type:
            downstream = AgentRegistry.get(downstream_type)
            if downstream:
                print(f"[{self.agent_type.name}] → [{downstream_type.name}]")
                downstream.from_upstream(data)
        else:
            print(f"[{self.agent_type.name}] End of flow")

    def send_to_upstream(self, data: AgentData) -> None:
        """Send data back to previous agent"""
        upstream_type = AgentGraph.get_upstream(self.agent_type)

        if upstream_type:
            upstream = AgentRegistry.get(upstream_type)
            if upstream:
                print(f"[{self.agent_type.name}] ← [{upstream_type.name}]")
                upstream.from_downstream(data)
        else:
            print(f"[{self.agent_type.name}] No upstream agent")

    def run_agent_loop(self, problem_query: str) -> Optional[AllToolParams]:
        """Run agent service with current memory"""
        if not self.project_path:
            raise ValueError(f"Project path must be set for {self.agent_type.name}")

        agent_service = AgentService(
            agent_name=self.agent_type,
            project_path=self.project_path,
            sutra_memory=self.memory,
        )
        return agent_service.solve_problem(problem_query)

    def save_memory_snapshot(self) -> None:
        """Save current memory state for potential reuse by other agents"""
        memory_state = self.memory.export_memory_state()
        self._memory_store[self._agent_instance_id] = memory_state

    def load_memory_from_agent(
        self, source_agent: "BaseAgent", preserve_sections: Optional[Set[str]] = None
    ) -> bool:
        """Load memory from another agent with selective preservation"""
        if source_agent._agent_instance_id not in self._memory_store:
            return False

        source_state = self._memory_store[source_agent._agent_instance_id]

        if preserve_sections:
            filtered_state = self._filter_memory_sections(
                source_state, preserve_sections
            )
            return self.memory.import_memory_state(filtered_state)

        return self.memory.import_memory_state(source_state)

    def copy_memory_from_agent(
        self,
        source_agent: "BaseAgent",
        sections_to_copy: Optional[Set[str]] = None,
        clear_sections: Optional[Set[str]] = None,
    ) -> bool:
        """Copy memory from another agent with selective sections and clearing"""
        if source_agent._agent_instance_id not in self._memory_store:
            return False

        source_state = deepcopy(self._memory_store[source_agent._agent_instance_id])

        if sections_to_copy:
            source_state = self._filter_memory_sections(source_state, sections_to_copy)

        if clear_sections:
            source_state = self._clear_memory_sections(source_state, clear_sections)

        return self.memory.import_memory_state(source_state)

    def get_last_memory_snapshot(self) -> bool:
        """Reload agent's own last saved memory state"""
        if self._agent_instance_id not in self._memory_store:
            return False

        last_state = self._memory_store[self._agent_instance_id]
        return self.memory.import_memory_state(last_state)

    def clear_memory_sections(self, sections: Set[str]) -> None:
        """Clear specific sections from current memory"""
        current_state = self.memory.export_memory_state()
        cleared_state = self._clear_memory_sections(current_state, sections)
        self.memory.import_memory_state(cleared_state)

    @staticmethod
    def _filter_memory_sections(state: dict, sections: Set[str]) -> dict:
        """Filter memory state to only include specified sections"""
        filtered = {}
        for section in sections:
            if section in state:
                filtered[section] = state[section]
        return filtered

    @staticmethod
    def _clear_memory_sections(state: dict, sections: Set[str]) -> dict:
        """Clear specified sections from memory state"""
        cleared = deepcopy(state)
        for section in sections:
            if section == "tasks":
                cleared["tasks"] = {}
            elif section == "history":
                cleared["history"] = []
            elif section == "code_snippets":
                cleared["code_snippets"] = {}
            elif section == "file_changes":
                cleared["file_changes"] = []
            elif section == "feedback_section":
                cleared["feedback_section"] = None
            elif section == "project_info":
                cleared["project_info"] = None
            elif section == "counters":
                pass
            elif section in cleared:
                if isinstance(cleared[section], list):
                    cleared[section] = []
                elif isinstance(cleared[section], dict):
                    cleared[section] = {}
                else:
                    cleared[section] = None
        return cleared
