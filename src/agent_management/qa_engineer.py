from pathlib import Path
from typing import Optional

from baml_client.types import Agent

from .base import AgentData, BaseAgent


class QAEngineerAgent(BaseAgent):
    def __init__(self, project_path: Optional[Path] = None):
        super().__init__(Agent.QAEngineer, project_path)
        self.developer_agent = None

    def from_upstream(self, data: AgentData) -> None:
        print(f"\n[{self.agent_type.name}] Received data from Developer")
        print(f"[{self.agent_type.name}] Context: {data.context[:100]}...")

        if self.developer_agent:
            self.copy_memory_from_agent(
                self.developer_agent,
                sections_to_copy={"code_snippets"},
                clear_sections={"history", "tasks"},
            )
            print(
                f"[{self.agent_type.name}] Copied code snippets from Developer (history and tasks cleared)"
            )

        self.run_agent_loop("Run QA tests on the codebase")
        tests_passed = self._check_test_results()

        if tests_passed:
            result_data = AgentData(context="tests_passed")
            print(
                f"\n[{self.agent_type.name}] All tests passed! Sending results to Developer"
            )
        else:
            result_data = AgentData(context="tests_failed")
            print(
                f"\n[{self.agent_type.name}] Tests failed. Sending failures to Developer"
            )

        self.send_to_upstream(result_data)

    def from_downstream(self, data: AgentData) -> None:
        pass

    def _check_test_results(self) -> bool:
        return True
