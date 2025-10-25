from pathlib import Path
from typing import Optional

from baml_client.types import Agent
from services.agent.memory_management.models import MemorySection

from .base import AgentData, BaseAgent


class QAEngineerAgent(BaseAgent):
    def __init__(self, project_path: Optional[Path] = None):
        super().__init__(Agent.QAEngineer, project_path)

    def from_upstream(self, data: AgentData) -> None:
        print(f"\n[{self.agent_type.name}] Received data from Developer")
        print(f"[{self.agent_type.name}] Context: {data.context[:100]}...")

        self.copy_memory_from_agent(
            Agent.Developer,
            sections_to_copy={MemorySection.CODE_SNIPPETS},
        )
        print(f"[{self.agent_type.name}] Copied code snippets from Developer")

        agent_data = self.run_agent_loop("Run QA tests on the codebase")

        result_data = AgentData(context="tests_passed")
        print(
            f"\n[{self.agent_type.name}] All tests passed! Sending results to Developer"
        )

        self.send_to_upstream(result_data)

    def from_downstream(self, data: AgentData) -> None:
        pass
