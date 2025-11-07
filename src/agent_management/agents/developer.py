from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

from baml_client.types import Agent, DeveloperCompletionParams
from services.agent.memory_management.models import MemorySection
from src.agent_management.types.agent import AgentData
from src.agent_management.utils.diff_utils import (
    format_diffs_for_message,
    generate_diffs_from_content_map,
)

from .base import BaseAgent


class DeveloperAgent(BaseAgent):
    def __init__(
        self, project_path: Path, parent_key: Optional[Tuple[Agent, Path]] = None
    ):
        super().__init__(Agent.Developer, project_path, parent_key)

    def run_agent_loop(self, problem_query: str) -> DeveloperCompletionParams:
        result = super().run_agent_loop(problem_query)
        assert isinstance(
            result, DeveloperCompletionParams
        ), "Expected DeveloperCompletionParams from parent"
        return result

    def from_upstream(self, data: AgentData) -> None:
        self.run_prerequisites()

        self.copy_memory_from_agent(
            agent_key=self.parent_key,
            sections_to_copy={MemorySection.CODE_SNIPPETS},
        )

        context = data.format_conversation(current_agent=self.agent_type)

        response = self.run_agent_loop(context)

        give_up = response.give_up

        if not give_up:
            new_data = AgentData(conversation=data.conversation.copy(), success=True)

            message = self._append_diffs_to_message(response.result)
            new_data.add_message(self.agent_type, message)
            self.send_to_downstream(new_data)

        if give_up:
            new_data = AgentData.from_context(response.result, self.agent_type)
            new_data.success = False
            new_data.project_path = self.project_path
            self.send_to_upstream(new_data)

    def from_downstream(self, data: AgentData) -> None:
        tests_passed = data.success

        if not tests_passed:
            self.run_prerequisites()
            self.clear_memory_sections({MemorySection.TASKS})

            context = data.format_conversation(current_agent=self.agent_type)
            response = self.run_agent_loop(context)

            give_up = response.give_up

            if not give_up:
                new_data = AgentData(
                    conversation=data.conversation.copy(), success=True
                )

                message = self._append_diffs_to_message(response.result)
                new_data.add_message(self.agent_type, message)
                self.send_to_downstream(new_data)

            if give_up:
                new_data = AgentData.from_context(response.result, self.agent_type)
                new_data.success = False
                new_data.project_path = self.project_path
                self.send_to_upstream(new_data)

        if tests_passed:
            new_data = AgentData(
                success=True,
                conversation=data.conversation.copy(),
                project_path=self.project_path,
            )
            new_data.add_message(
                self.agent_type,
                "I have made all the requested changes and tested them successfully",
            )
            self.send_to_upstream(new_data)

    def _append_diffs_to_message(self, message: str) -> str:
        if self.file_content_map:
            logger.debug(
                f"[{self.agent_type.name}] Generating diffs for {len(self.file_content_map)} files"
            )
            diffs = generate_diffs_from_content_map(self.file_content_map)
            diff_message = format_diffs_for_message(diffs)
            message += diff_message
            self.clear_file_content_map()
        return message
