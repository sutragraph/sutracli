from pathlib import Path
from typing import Optional

from baml_client.types import Agent, DeveloperCompletionParams
from services.agent.memory_management.models import MemorySection
from src.agent_management.types.agent import AgentData

from .base import BaseAgent


class DeveloperAgent(BaseAgent):
    def __init__(self, project_path: Optional[Path] = None):
        super().__init__(Agent.Developer, project_path)

    def run_agent_loop(self, problem_query: str) -> DeveloperCompletionParams:
        result = super().run_agent_loop(problem_query)
        assert isinstance(
            result, DeveloperCompletionParams
        ), "Expected DeveloperCompletionParams from parent"
        return result

    def from_upstream(self, data: AgentData) -> None:
        self.run_prerequisites()

        context = data.format_conversation(current_agent=self.agent_type)

        response = self.run_agent_loop(context)

        give_up = response.give_up

        if not give_up:
            new_data = AgentData(conversation=data.conversation.copy(), success=True)
            new_data.add_message(self.agent_type, response.result)
            self.send_to_downstream(new_data)

        if give_up:
            new_data = AgentData.from_context(response.result, self.agent_type)
            new_data.success = False
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
                new_data.add_message(self.agent_type, response.result)
                self.send_to_downstream(new_data)

            if give_up:
                new_data = AgentData.from_context(response.result, self.agent_type)
                new_data.success = False
                self.send_to_upstream(new_data)

        if tests_passed:
            new_data = AgentData(conversation=data.conversation.copy(), success=True)
            new_data.add_message(
                self.agent_type,
                "I have made all the requested changes and tested them successfully",
            )
            self.send_to_upstream(new_data)
