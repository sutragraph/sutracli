from pathlib import Path
from typing import Optional

from baml_client.types import Agent

from .base import AgentData, BaseAgent


class DeveloperAgent(BaseAgent):
    def __init__(self, project_path: Optional[Path] = None):
        super().__init__(Agent.Developer, project_path)
        self.qa_agent = None

    def from_upstream(self, data: AgentData) -> None:
        print(f"\n[{self.agent_type.name}] Received task from Roadmap")
        print(f"[{self.agent_type.name}] Context: {data.context[:100]}...")

        self.run_agent_loop("Complete development tasks")
        self.save_memory_snapshot()

        result_data = AgentData(context="development_complete")
        print(f"\n[{self.agent_type.name}] Sending work to QA Engineer")
        self.send_to_downstream(result_data)

    def from_downstream(self, data: AgentData) -> None:
        print(f"\n[{self.agent_type.name}] Received QA results")

        if "tests_passed" in data.context:
            print(
                f"[{self.agent_type.name}] All tests passed! Sending success to Roadmap"
            )
            success_data = AgentData(context="success")
            self.send_to_upstream(success_data)
        else:
            print(f"[{self.agent_type.name}] Tests failed. Fixing issues...")

            self.get_last_memory_snapshot()
            self.clear_memory_sections({"tasks"})

            self.run_agent_loop("Fix failing tests")
            self.save_memory_snapshot()

            result_data = AgentData(context="fixes_complete")
            print(f"\n[{self.agent_type.name}] Sending fixed code to QA Engineer")
            self.send_to_downstream(result_data)
