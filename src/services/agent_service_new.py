"""Agent Service with unified tool status handling."""

import time
from typing import Dict, Any, List, Optional, Iterator, Union
from loguru import logger
from rich.prompt import Confirm
from rich.panel import Panel
from rich.text import Text
from utils.console import console
from tools import execute_tool

from baml_client.types import SutraMemoryParams
from .agent.session_management import SessionManager
from .agent.memory_management import SutraMemoryManager
from .project_manager import ProjectManager
from pathlib import Path


from agents_new import Agent, execute_agent, AgentResponse, RoadmapResponse, RoadmapCompletionParams, BaseCompletionParams


class AgentService:
    """Agent Service with unified tool status handling."""

    def __init__(
        self, session_id: Optional[str] = None, project_path: Optional[str] = None
    ):
        """Initialize the Agent Service.

        Args:
            session_id: Optional session ID for conversation continuity
            project_path: Optional path to the project directory. If None, uses current directory.

        """

        self.session_manager = SessionManager.get_or_create_session(session_id)
        self.memory_manager = SutraMemoryManager()

        self.project_manager = ProjectManager(self.memory_manager)

        self.last_tool_result = None
        self.result = None

        self._memory_needs_update = False

        self._consecutive_failures = 0

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens_used = 0
        self.llm_call_count = 0

        # Prompt user to confirm indexing if project is not indexed
        project_path_obj = Path(project_path) if project_path else Path.cwd()

        self.current_project_name = self.project_manager.determine_project_name(
            project_path_obj
        )

        is_project_indexed = self.project_manager.check_project_exists(
            self.current_project_name
        )

        self._should_index_current_project = not is_project_indexed

        if not is_project_indexed:
            self._prompt_and_index_project(project_path_obj)

    def _prompt_and_index_project(self, project_path: Path) -> None:
        """Prompt user to index the current project if it's not already indexed.

        Args:
            project_path: Path to the project directory
        """
        try:
            # Create informative panel about the current project
            project_info = Text()
            project_info.append(f"Project Name: ", style="bold blue")
            project_info.append(f"{self.current_project_name}\n", style="white")
            project_info.append(f"Project Path: ", style="bold blue")
            project_info.append(f"{project_path}\n", style="white")
            project_info.append(f"Status: ", style="bold blue")
            project_info.append("Not indexed", style="red")

            panel = Panel(
                project_info,
                title="[bold yellow]Project Not Found[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            )

            console.print()
            console.print(panel)
            console.print()

            self._should_index_current_project = Confirm.ask(
                "[bold cyan]Would you like to index this repository now?[/bold cyan]",
                default=True
            )

            if self._should_index_current_project:
                console.print()  # Add blank line
                console.process("Starting project indexing...")

                try:
                    # Perform the indexing
                    self.project_manager.auto_index_project(
                        self.current_project_name,
                        project_path
                    )

                    console.success(f"Successfully indexed project '{self.current_project_name}'")

                except Exception as e:
                    logger.error(f"Failed to index project: {e}")
                    console.error(f"Failed to index project: {e}")
                    console.warning("Continuing with limited functionality...")

            else:
                console.warning("Project indexing skipped. Some features may be limited.")

        except Exception as e:
            logger.error(f"Error during project indexing prompt: {e}")
            console.error(f"Error during indexing setup: {e}")

    def solve_problem(self, problem_query: str) -> Union[RoadmapCompletionParams, BaseCompletionParams, Dict[str, Any]]:
        # if (self._should_index_current_project):
        #     console.warning("Project is not indexed. Some features may be limited.")
        # else:
        #     # Perform incremental indexing
        #     indexing_result = self.project_manager.perform_incremental_indexing(
        #         self.current_project_name
        #     )

        query_id = self.session_manager.start_new_query(problem_query)
        self.session_manager.set_problem_context(problem_query)

        logger.debug(f"Session {self.session_manager.session_id} - Starting new query {query_id}")

        current_iteration = 0
        max_iterations = 50

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.info(f"Iteration {current_iteration}/{max_iterations}")

            user_message = self._build_user_message(problem_query, current_iteration)

            # change this to as per user selection XXXX
            agent_name = Agent.ROADMAP

            logger.debug(f"Invoking agent: {agent_name}")

            agent_response: AgentResponse = execute_agent(
                agent_name,
                context=user_message
            )

            # Check if completion occurred
            is_completion = self._parse_agent_response(agent_response)

            if is_completion:
                return self.result if self.result else {"result": "Task completed"}  # ignore: R1720

        return {"result": "Max iterations reached without completion."}

    def _build_user_message(self, problem_query: str, current_iteration: int) -> str:
        user_message = []

        user_message.append(f"User Query: {problem_query}\n")

        memory_status = self._build_memory_status(current_iteration)
        user_message.append(memory_status)

        task_progress = self.session_manager.get_task_progress_history()
        if task_progress and task_progress.strip():
            user_message.append(f"\nTASK PROGRESS HISTORY\n\n{task_progress}\n")

        user_message.append(f"\nTOOL STATUS\n\n{self.last_tool_result}\n")

        return "\n".join(user_message)

    def _build_memory_status(self, current_iteration: int) -> str:
        if current_iteration == 1:
            memory_status = "No previous memory available. This is first message from user."
            logger.debug("Agent: First iteration with empty memory")
            return f"\nSUTRA MEMORY STATUS\n\n{memory_status}"
        else:
            sutra_memory_rich = self.memory_manager.get_memory_for_llm()
            if sutra_memory_rich and sutra_memory_rich.strip():
                logger.debug("Agent: Using existing Sutra memory from previous iterations")
                return f"\nSUTRA MEMORY STATUS\n\n{sutra_memory_rich}\n"
            else:
                memory_status = "No previous memory available."
                logger.debug("Agent: No memory available")
                return f"\nSUTRA MEMORY STATUS\n\n{memory_status}\n"

    def _parse_agent_response(self, response: AgentResponse) -> bool:
        """Parse agent response and return True if completion occurred."""
        match response.agent_type:
            case Agent.ROADMAP:
                return self._parse_roadmap_response(response.content)

            case _:
                logger.warning(f"Unknown agent type: {response.agent_type}")
                return False

    def _parse_roadmap_response(self, content: RoadmapResponse) -> bool:
        """Parse roadmap response and return True if completion occurred."""
        is_completion = False

        if content.thinking and content.thinking.strip():
            self._parse_thinking(content.thinking)

        tool_to_execute = content.tool_call

        if tool_to_execute:
            tool_name = tool_to_execute.tool_name
            tool_params = tool_to_execute.parameters.model_dump()

            # Check if this was a completion call and capture parameters
            if tool_name == "attempt_completion":
                is_completion = True
                self.result = tool_to_execute.parameters

            # Execute tool for formatting and display
            self.last_tool_result = execute_tool(
                Agent.ROADMAP,
                tool_name,
                tool_params
            )

        if content.sutra_memory:
            self._parse_sutra_memory(content.sutra_memory)

        return is_completion

    def _parse_thinking(self, thinking: str) -> None:
        console.print("🤔 [bold dim]Thinking...[/bold dim]")
        for line in thinking.split('\n'):
            if line.strip():
                console.print(f"   [thinking]{line}[/thinking]")
            else:
                console.print()

    def _parse_sutra_memory(self, sutra_memory: SutraMemoryParams) -> None:
        results = self.memory_manager.process_sutra_memory_params(sutra_memory)

        # Update session memory if any changes were made
        if results["success"] and any(results["changes_applied"].values()):
            try:
                # Get the rich formatted memory from memory manager (includes code snippets)
                memory_summary = self.memory_manager.get_memory_for_llm()
                # Update session manager with the rich memory content
                self.session_manager.update_sutra_memory(memory_summary)
                logger.debug(f"Updated Sutra Memory in session: {len(memory_summary)} characters")
                logger.debug(f"Memory includes {len(self.memory_manager.get_all_code_snippets())} code snippets")
            except Exception as e:
                logger.error(f"Error updating session memory: {e}")
            logger.debug(
                f"Processed sutra memory changes: {sum(len(v) for v in results['changes_applied'].values())} total changes")
