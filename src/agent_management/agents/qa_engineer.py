from pathlib import Path
from typing import Optional

from loguru import logger

from baml_client.types import Agent, QAEngineerCompletionParams
from services.agent.memory_management.models import MemorySection
from src.agent_management.types.agent import AgentData

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
        logger.debug(f"[{self.agent_type.name}] Context: {data.context[:100]}...")

        self.run_prerequisites()

        self.copy_memory_from_agent(
            Agent.Developer,
            sections_to_copy={MemorySection.CODE_SNIPPETS},
        )

        changes_context = ""
        if self.indexing_changes:
            diffs = self.indexing_changes.get("diffs", [])
            if diffs:
                changes_context = "\n\nDiff of changes made:\n"
                for diff in diffs:
                    changes_context += f"{diff}\n"

        problem_query = f"I made the following changes to the codebase. Create and run tests to validate these changes:\n\n{data.context}{changes_context}"

        response = self.run_agent_loop(problem_query)
        result_data = self.format_response_for_upstream(response)

        self.send_to_upstream(result_data)

    def from_downstream(self, data: AgentData) -> None:
        pass

    def format_response_for_upstream(
        self, response: QAEngineerCompletionParams
    ) -> AgentData:
        if response.failed_tests and len(response.failed_tests) > 0:
            logger.debug(
                f"[{self.agent_type.name}] Tests failed: {len(response.failed_tests)}. Sending failure to Developer"
            )

            context = "Failed Tests:\n"
            for i, test in enumerate(response.failed_tests, 1):
                context += f'{i}. "{test.test_name}" : "{test.test_details}"\n'

            return AgentData(
                context=context,
                success=False,
            )
        return AgentData(context=response.result, success=True)
