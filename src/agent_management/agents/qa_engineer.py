from pathlib import Path
from typing import List, Optional

from loguru import logger

from baml_client.types import (
    Agent,
    QAEngineerCompletionParams,
    QAEngineerFailedTestsParams,
)
from services.agent.memory_management.models import MemorySection
from src.agent_management.types.agent import AgentData
from src.agent_management.utils.qa_utils import format_failed_tests_message

from .base import BaseAgent


class QAEngineerAgent(BaseAgent):
    def __init__(self, project_path: Optional[Path] = None):
        super().__init__(Agent.QAEngineer, project_path)

    def run_agent_loop(self, problem_query: str) -> QAEngineerCompletionParams:
        result = super().run_agent_loop(problem_query)
        assert isinstance(
            result, QAEngineerCompletionParams
        ), "Expected DeveloperCompletionParams from parent"
        return result

    def from_upstream(self, data: AgentData) -> None:
        logger.debug(f"\n[{self.agent_type.name}] Received data from Developer")

        self.run_prerequisites()

        self.copy_memory_from_agent(
            Agent.Developer,
            sections_to_copy={MemorySection.CODE_SNIPPETS, MemorySection.HISTORY},
        )

        last_roadmap_msg = data.get_last_message(Agent.Roadmap)

        changes_context = ""
        if self.indexing_changes:
            diffs = self.indexing_changes.get("diffs", [])
            if diffs:
                changes_context = "\n\nDiff of changes made:\n"
                for diff in diffs:
                    changes_context += f"{diff}\n"

        problem_query = f"I made the following changes to the codebase. Create and run tests to validate these changes:\n\n{last_roadmap_msg}{changes_context}"

        response = self.run_agent_loop(problem_query)

        new_data = AgentData(
            conversation=data.conversation.copy(),
            success=response.failed_tests is None or len(response.failed_tests) == 0,
        )
        new_data.add_message(
            self.agent_type,
            (
                response.result
                if new_data.success
                else format_failed_tests_message(
                    response.failed_tests, self.agent_type.name
                )
            ),
        )

        self.send_to_upstream(new_data)

    def from_downstream(self, data: AgentData) -> None:
        pass
