"""Agent Service with unified tool status handling."""

from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from baml_client.types import Agent
from src.agent_management.core.executor import execute_agent
from src.agent_management.types.agent import AgentResponse
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
    ):
        """Initialize the Agent Service.

        Args:
            session_id: Optional session ID for conversation continuity

        """
        if project_path is None:
            raise ValueError("Project path must be provided")

        if agent_name is None:
            raise ValueError("Agent name must be provided")

        self.agent_name = agent_name
        self.session_manager = SessionManager.get_or_create_session(session_id)
        self.memory_manager = sutra_memory or SutraMemoryManager()

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
                            return None

                # Store current problem query for potential modification during file verification
                self._current_problem_query = problem_query

                user_message = self._build_user_message(problem_query)

                logger.debug(f"Invoking agent: {self.agent_name}")

                agent_response = execute_agent(self.agent_name, context=user_message)

                # Check if completion occurred
                is_completion = self._parse_response(
                    agent_response.agent_type, agent_response
                )
                logger.debug(f"Is completion: {is_completion}")
                if is_completion:
                    # Check if this is a roadmap agent and if post-processing requests continuation
                    if self.agent_name == Agent.Roadmap and self.result:
                        post_result = self._handle_roadmap_post_processing()

                        # If user provided feedback, continue the loop with that feedback
                        if (
                            post_result
                            and post_result.get("continue_roadmap")
                            and post_result.get("feedback")
                        ):
                            # Store the formatted roadmap prompts in sutra memory feedback section
                            feedback = post_result.get("feedback")
                            self._store_feedback_in_sutra_memory(feedback)

                            # Set feedback tool status for next iteration
                            self._set_feedback_tool_status(feedback)

                            # Update the problem query from the stored version (may have been modified during file verification)
                            problem_query = self._current_problem_query

                            # Continue the loop instead of returning - this preserves the session
                            continue

                    return self.result

        except KeyboardInterrupt:
            console.print()
            console.print("[yellow]Task interrupted by user.[/yellow]")
            return None

        return None

    def _handle_roadmap_post_processing(self) -> Optional[Dict[str, Any]]:
        """Handle roadmap post-processing and return continuation info if needed."""
        try:
            from src.agent_management.post_requisites.handlers import get_agent_handler

            logger.debug("Starting roadmap post-processing...")
            handler = get_agent_handler(self.agent_name)
            post_result = handler.process_agent_result_direct(self.result)

            return post_result

        except Exception as e:
            logger.error(f"Error in roadmap post-processing: {e}")
            return None

    def _store_feedback_in_sutra_memory(self, feedback: str) -> None:
        """Store user feedback and roadmap prompts in a dedicated FEEDBACK section in sutra memory."""
        try:
            # Get the formatted project prompts from the post-processing handlers
            from src.agent_management.post_requisites.handlers import (
                RoadmapAgentHandler,
            )

            handler = RoadmapAgentHandler()
            project_prompts = handler._convert_roadmap_to_prompts(
                self.result.model_dump()
            )

            # Create FEEDBACK section in sutra memory
            feedback_section = "FEEDBACK SECTION: \n"
            feedback_section += f"USER FEEDBACK: {feedback}\n\n"

            # Add information about the generated project roadmaps
            feedback_section += (
                f"GENERATED PROJECT ROADMAPS ({len(project_prompts)} projects):\n\n"
            )

            for i, project_prompt in enumerate(project_prompts, 1):
                feedback_section += f"=== PROJECT {i} Roadmap ===\n"
                feedback_section += (
                    f"Project Path: {project_prompt.get('project_path', 'Unknown')}\n\n"
                )
                feedback_section += project_prompt.get("prompt", "No prompt available")

            self.memory_manager.set_feedback_section(feedback_section)

            logger.debug(
                f"Stored feedback and {len(project_prompts)} roadmap prompts in FEEDBACK section"
            )

        except Exception as e:
            logger.error(f"Error storing feedback in sutra memory: {e}")

    def _set_feedback_tool_status(self, user_feedback) -> None:
        """Set tool status to show feedback information instead of attempt_completion."""
        try:
            # Enhanced feedback tool status with roadmap information
            feedback_status = "Tool: feedback_received\n"
            feedback_status += "Status: User provided feedback for roadmap improvement. The generated project roadmaps are stored in FEEDBACK section. Create new task for these improvements and work on it.\n"
            feedback_status += f"Feedback: {user_feedback}\n"

            # Set this as the last tool result
            self.last_tool_result = feedback_status

            logger.debug("Set enhanced feedback tool status with roadmap information")

        except Exception as e:
            logger.error(f"Error setting feedback tool status: {e}")
            # Fallback to simple feedback status
            self.last_tool_result = "Tool: feedback_received\nStatus: User provided feedback for roadmap improvement."

    def _build_user_message(self, problem_query: str) -> str:
        user_message = []

        user_message.append(f"User Query: {problem_query}\n")

        memory_status = self._build_memory_status()
        user_message.append(memory_status)

        user_message.append(f"\nTOOL STATUS\n\n{self.last_tool_result}\n")

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
        """Parse roadmap response and return True if completion occurred."""
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

            # Check if this was a completion call and capture parameters
            if tool_name == "attempt_completion":
                is_completion = True
                self.result = tool_to_execute.parameters

                # Do file path verification BEFORE displaying anything to user
                if self._should_verify_file_paths():
                    verification_result = self._verify_file_paths_before_display()

                    if not verification_result["valid"]:
                        # File paths are invalid - return False to continue agent loop
                        # Set feedback for next iteration
                        feedback = verification_result["feedback"]
                        self._store_feedback_in_sutra_memory(feedback)
                        self._set_feedback_tool_status(feedback)

                        # Modify problem query for next iteration
                        if hasattr(self, "_current_problem_query"):
                            if "FILE DOES NOT EXIST" in feedback:
                                self._current_problem_query = f"{self._current_problem_query}\n\nIMPORTANT: The provided file paths for modify or delete operations do not exist. {feedback}"
                            else:
                                self._current_problem_query = f"{self._current_problem_query}\n\nUser feedback for improvement: {feedback}"

                        return False  # Don't show completion, continue agent loop

            # Execute tool for formatting and display (only if file paths are valid)
            self.last_tool_result = execute_tool(agent, tool_name, tool_params)

        return is_completion

    def _should_verify_file_paths(self) -> bool:
        """Check if we should verify file paths for this agent."""
        return self.agent_name == Agent.Roadmap

    def _verify_file_paths_before_display(self) -> Dict[str, Any]:
        """Verify file paths before displaying project info to user."""
        try:
            from src.agent_management.post_requisites.handlers import (
                RoadmapAgentHandler,
            )

            handler = RoadmapAgentHandler()
            roadmap_data = self.result.model_dump()
            result = handler._verify_file_paths(roadmap_data)
            return result

        except Exception as e:
            logger.error(f"Error during file path verification: {e}")
            # If verification fails, assume paths are valid to avoid blocking
            return {"valid": True}

    def _parse_thinking(self, thinking: str) -> None:
        header = Text("THINKING", style="bold yellow")

        content_lines = []
        for line in thinking.split("\n"):
            if line.strip():
                content_lines.append(line)
            else:
                content_lines.append("")  # Preserve empty lines

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

        # Update session memory if any changes were made
        if results["success"] and any(results["changes_applied"].values()):
            try:
                # Get the rich formatted memory from memory manager (includes code snippets)
                memory_summary = self.memory_manager.get_memory_for_llm()
                # Update session manager with the rich memory content
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
