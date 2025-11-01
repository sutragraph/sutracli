"""Agent Service with unified tool status handling."""

from pathlib import Path
from typing import Optional

from loguru import logger
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from baml_client.types import Agent
from src.agent_management.core.executor import execute_agent
from src.agent_management.types.agent import AgentResponse
from src.agent_management.types.exception import AgentErrorType
from src.graph.project_indexer import ProjectIndexer
from src.utils.error_utils import raiseError
from tools import AllSutraMemoryParams, AllToolParams, execute_tool
from utils.console import console

from .agent.memory_management import SutraMemoryManager
from .agent.session_management import SessionManager


class AgentService:
    """Agent Service with unified tool status handling."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        agent_name: Optional[Agent] = None,
        project_path: Optional[Path] = None,
        sutra_memory: Optional[SutraMemoryManager] = None,
        file_content_map: Optional[dict] = None,
    ):
        """Initialize the Agent Service.

        Args:
            session_id: Optional session ID for conversation continuity
            file_content_map: Reference to agent's file content map (for tracking changes after tool calls)

        """
        if project_path is None:
            raise ValueError("Project path must be provided")

        if agent_name is None:
            raise ValueError("Agent name must be provided")

        self.agent_name = agent_name
        self.project_path = project_path
        self.session_manager = SessionManager.get_or_create_session(session_id)
        self.memory_manager = sutra_memory or SutraMemoryManager()
        self.file_content_map = file_content_map
        self.indexer = ProjectIndexer()

        self.last_tool_result = None
        self.result = None

    def solve_problem(self, problem_query: str) -> AllToolParams:
        query_id = self.session_manager.start_new_query(problem_query)
        self.session_manager.set_problem_context(problem_query)

        logger.debug(
            f"Session {self.session_manager.session_id} - Starting new query {query_id}"
        )
        current_iteration = 0
        max_iterations = 70

        try:
            while current_iteration < max_iterations:
                current_iteration += 1

                if current_iteration % 15 == 0:
                    console.print()
                    console.print(
                        f"[yellow]Completed {current_iteration} iterations. Current progress:[/yellow]"
                    )

                    remaining = max_iterations - current_iteration
                    if remaining > 0:
                        should_continue = Confirm.ask(
                            f"[bold cyan]Continue with the remaining {remaining} iterations?[/bold cyan]",
                            default=True,
                        )

                        if not should_continue:
                            console.print(
                                f"[yellow]Task stopped by user after {current_iteration} iterations.[/yellow]"
                            )
                            raiseError(
                                AgentErrorType.USER_CANCELLED,
                                f"Task stopped by user after {current_iteration} iterations",
                                RuntimeError,
                            )

                self._current_problem_query = problem_query

                user_message = self._build_user_message(problem_query)

                logger.debug(f"Invoking agent: {self.agent_name}")

                agent_response = execute_agent(self.agent_name, context=user_message)

                is_completion = self._parse_response(
                    agent_response.agent_type, agent_response
                )
                logger.debug(f"Is completion: {is_completion}")
                if is_completion:
                    if self.result is None:
                        raiseError(
                            AgentErrorType.COMPLETION_WITHOUT_RESULT,
                            "Agent signaled completion but no result was set",
                            RuntimeError,
                        )
                    return self.result

        except KeyboardInterrupt:
            console.print()
            console.print("[yellow]Task interrupted by user.[/yellow]")
            raise  # Re-raise KeyboardInterrupt to propagate it up

        raiseError(
            AgentErrorType.MAX_ITERATIONS_REACHED,
            f"Maximum iterations ({max_iterations}) reached without completion",
            RuntimeError,
        )

    def _build_user_message(self, problem_query: str) -> str:
        user_message = []

        user_message.append(f"User Query: {problem_query}\n")

        memory_status = self._build_memory_status()
        user_message.append(memory_status)

        user_message.append(f"\nTOOL STATUS\n{self.last_tool_result}\n")

        return "\n".join(user_message)

    def _build_memory_status(self) -> str:
        sutra_memory_rich = self.memory_manager.get_memory_for_llm()

        if sutra_memory_rich and sutra_memory_rich.strip():
            logger.debug("Agent: Using Sutra memory from memory manager")
            return f"\nSUTRA MEMORY STATUS\n\n{sutra_memory_rich}\n"
        else:
            memory_status = "No previous memory available."
            logger.debug("Agent: No memory available")
            return f"\nSUTRA MEMORY STATUS\n\n{memory_status}\n"

    def _parse_response(self, agent: Agent, response: AgentResponse) -> bool:
        is_completion = False
        content = response.content

        if content.sutra_memory:
            self._parse_sutra_memory(content.sutra_memory)

        if content.thinking and content.thinking.strip():
            self._parse_thinking(content.thinking)

        tool_to_execute = content.tool_call

        if tool_to_execute:
            tool_name = tool_to_execute.tool_name
            tool_params = tool_to_execute.parameters.model_dump()

            if tool_name == "attempt_completion":
                is_completion = True
                self.result = tool_to_execute.parameters

            self.last_tool_result = execute_tool(agent, tool_name, tool_params)

            if (
                tool_name in ["edit_file", "terminal"]
                and self.file_content_map is not None
            ):
                self._run_indexing_after_tool(tool_name)

        return is_completion

    def _parse_thinking(self, thinking: str) -> None:
        header = Text("THINKING", style="bold yellow")

        content_lines = []
        for line in thinking.split("\n"):
            if line.strip():
                content_lines.append(line)
            else:
                content_lines.append("")

        content = Text("\n".join(content_lines), style="dim")

        thinking_panel = Panel(
            content,
            title=header,
            title_align="left",
            border_style="yellow",
            padding=(1, 1),
        )

        console.print(thinking_panel)

    def _parse_sutra_memory(self, sutra_memory: AllSutraMemoryParams) -> None:
        results = self.memory_manager.process_sutra_memory_params(sutra_memory)

        if results["success"] and any(results["changes_applied"].values()):
            try:
                memory_summary = self.memory_manager.get_memory_for_llm()
                self.session_manager.update_sutra_memory(memory_summary)
                logger.debug(
                    f"Updated Sutra Memory in session: {len(memory_summary)} characters"
                )
                logger.debug(
                    f"Memory includes {len(self.memory_manager.get_all_code_snippets())} code snippets"
                )
            except Exception as e:
                logger.error(f"Error updating session memory: {e}")
            logger.debug(
                f"Processed sutra memory changes: {sum(len(v) for v in results['changes_applied'].values())} total changes"
            )

    def _update_file_content_map(
        self, file_path: str, old_content: str, new_content: str
    ) -> None:
        if self.file_content_map is None:
            return

        if file_path in self.file_content_map:
            self.file_content_map[file_path]["new_content"] = new_content
            logger.debug(
                f"[{self.agent_name.name}] Updated existing entry for {file_path}"
            )
        else:
            self.file_content_map[file_path] = {
                "old_content": old_content,
                "new_content": new_content,
            }
            logger.debug(f"[{self.agent_name.name}] Added new entry for {file_path}")

    def _run_indexing_after_tool(self, tool_name: str) -> None:
        try:
            logger.debug(
                f"[{self.agent_name.name}] Running indexing after {tool_name} tool call"
            )

            # Get project name from database using project path
            project = self.indexer.connection.get_project_by_path(
                str(self.project_path)
            )
            if not project:
                logger.debug(f"Project not found for path: {self.project_path}")
                return

            project_name = project.name

            indexing_result = self.indexer.incremental_index_project(project_name)

            if (
                indexing_result
                and indexing_result.get("status") == "success"
                and self.file_content_map is not None
            ):
                old_content_map = indexing_result.get("old_content", {})
                project_dir = indexing_result.get("project_dir")
                changes = indexing_result.get("changes", {})

                if not project_dir:
                    logger.debug("No project_dir in indexing result")
                    return

                files_to_process = changes.get("changed_files", set()).union(
                    changes.get("new_files", set())
                )

                for file_path in files_to_process:
                    try:
                        rel_path = str(file_path.relative_to(project_dir))

                        new_content = self.indexer._get_file_content_from_db(
                            str(file_path)
                        )
                        old_content = old_content_map.get(rel_path, "")
                        self._update_file_content_map(
                            rel_path, old_content, new_content
                        )
                    except Exception as e:
                        logger.debug(f"Could not process {file_path}: {e}")

                deleted_files = changes.get("deleted_files", set())
                for file_path in deleted_files:
                    try:
                        rel_path = str(file_path.relative_to(project_dir))
                        old_content = old_content_map.get(rel_path, "")
                        new_content = ""
                        self._update_file_content_map(
                            rel_path, old_content, new_content
                        )
                    except Exception as e:
                        logger.debug(f"Could not process deleted file {file_path}: {e}")

                logger.debug(
                    f"[{self.agent_name.name}] Updated file_content_map with {len(self.file_content_map)} files"
                )

        except Exception as e:
            logger.error(f"Error running indexing after {tool_name}: {e}")
