"""Agent Service with unified tool status handling."""


from typing import Optional, Dict, Any
from loguru import logger
from rich.prompt import Confirm
from rich.panel import Panel
from rich.text import Text
from utils.console import console
from tools import execute_tool, AllToolParams

from baml_client.types import SutraMemoryParams
from .agent.session_management import SessionManager
from .agent.memory_management import SutraMemoryManager
from .project_manager import ProjectManager
from pathlib import Path


from agents_new import Agent, execute_agent, AgentResponse, RoadmapResponse


class AgentService:
    """Agent Service with unified tool status handling."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        agent_name: Optional[Agent] = None,
        project_path: Optional[Path] = None

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
        self.current_project_name = self.project_manager.determine_project_name(
            project_path
        )

        is_project_indexed = self.project_manager.check_project_exists(
            self.current_project_name
        )

        self._should_index_current_project = not is_project_indexed

        if not is_project_indexed:
            self._prompt_and_index_project(project_path)

    def _prompt_and_index_project(self, project_path: Path) -> None:
        """Prompt user to index the current project if it's not already indexed.

        Args:
            project_path: Path to the project directory
        """
        try:
            # Create informative panel about the current project
            project_info = Text()
            project_info.append("Project Name: ", style="bold blue")
            project_info.append(f"{self.current_project_name}\n", style="white")
            project_info.append("Project Path: ", style="bold blue")
            project_info.append(f"{project_path}\n", style="white")
            project_info.append("Status: ", style="bold blue")
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

    def run(self) -> Optional[AllToolParams]:
        """Run the agent with user prompting and problem solving.

        Returns:
            The result of the problem solving process
        """
        print("🚀 Welcome to Sutra Agent!")
        print("   I'm here to help you with coding, debugging, and knowledge sharing.")
        print("\n💬 How can I help you? Type your questions or requests below.")
        print("💡 Tip: Type 'exit', 'quit', 'bye', or 'goodbye' to end the session")

        # Get user input
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                print("-" * 40)

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                    print("\n👋 Goodbye! Session ended.")
                    return None

                # Got valid input, break out of input loop
                break
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Session ended.")
                return None
            except EOFError:
                print("\n\n👋 Goodbye! Session ended.")
                return None

        # Run agent session with the input
        print("🚀 Starting agent session...")
        return self.solve_problem(problem_query=user_input)

    def solve_problem(self, problem_query: str) -> Optional[AllToolParams]:
        if (self._should_index_current_project):
            console.warning("Project is not indexed. Some features may be limited.")
        else:
            # Perform incremental indexing
            self.project_manager.perform_incremental_indexing(
                self.current_project_name
            )

        query_id = self.session_manager.start_new_query(problem_query)
        self.session_manager.set_problem_context(problem_query)

        logger.debug(f"Session {self.session_manager.session_id} - Starting new query {query_id}")

        current_iteration = 0
        max_iterations = 50

        try:
            while current_iteration < max_iterations:
                current_iteration += 1
                if current_iteration == 15:
                    console.print()
                    console.print("[yellow]Completed 15 iterations. Current progress:[/yellow]")

                    should_continue = Confirm.ask(
                        f"[bold cyan]Continue with the remaining {
                            max_iterations - current_iteration} iterations?[/bold cyan]",
                        default=True
                    )

                    if not should_continue:
                        console.print("[yellow]Task stopped by user after 15 iterations.[/yellow]")
                        return None

                # Store current problem query for potential modification during file verification
                self._current_problem_query = problem_query

                user_message = self._build_user_message(problem_query, current_iteration)

                logger.debug(f"Invoking agent: {self.agent_name}")

                agent_response: AgentResponse = execute_agent(
                    self.agent_name,
                    context=user_message
                )

                # Check if completion occurred
                is_completion = self._parse_agent_response(agent_response)
                logger.debug(f"Is completion: {is_completion}")
                if is_completion:
                    # Check if this is a roadmap agent and if post-processing requests continuation
                    if self.agent_name == Agent.ROADMAP and self.result:
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
                feedback_section += f"=== PROJECT {i} ROADMAP ===\n"
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
                logger.debug("Agent: Using Sutra memory from memory manager")
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
                        if hasattr(self, '_current_problem_query'):
                            if "FILE DOES NOT EXIST" in feedback:
                                self._current_problem_query = f"{self._current_problem_query}\n\nIMPORTANT: The provided file paths for modify or delete operations do not exist. {feedback}"
                            else:
                                self._current_problem_query = f"{self._current_problem_query}\n\nUser feedback for improvement: {feedback}"

                        return False  # Don't show completion, continue agent loop

            # Execute tool for formatting and display (only if file paths are valid)
            self.last_tool_result = execute_tool(
                Agent.ROADMAP,
                tool_name,
                tool_params
            )

        return is_completion

    def _should_verify_file_paths(self) -> bool:
        """Check if we should verify file paths for this agent."""
        return self.agent_name == Agent.ROADMAP

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
        for line in thinking.split('\n'):
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
