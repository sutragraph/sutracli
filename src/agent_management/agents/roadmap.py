from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from loguru import logger
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

from agent_management.types.agent import AgentData
from agent_management.utils.roadmap_utils import (
    convert_roadmap_to_prompts,
    format_agents_result,
    format_feedback_section,
    format_feedback_tool_status,
    separate_results_by_status,
    verify_roadmap_file_paths,
)
from baml_client.types import Agent, BaseCompletionParams, RoadmapCompletionParams
from config.settings import get_config
from utils.console import console

from .base import BaseAgent


class RoadmapAgent(BaseAgent):
    def __init__(
        self, project_path: Path, parent_key: Optional[Tuple[Agent, Path]] = None
    ):
        super().__init__(Agent.Roadmap, project_path, parent_key)
        self.spawned_agent_results: List[AgentData] = []
        self.spawned_agent_count = 0

    def from_upstream(self, data: AgentData) -> None:
        response = data.format_conversation()

        self.run_agent_loop(response)

    def from_downstream(self, data: AgentData) -> None:
        """Save the result in spawned_agent_results array till all the sub agents are done"""

        self.spawned_agent_results.append(data)

        if self.spawned_agent_count == len(self.spawned_agent_results):
            self._on_all_agents_complete()

    def _on_all_agents_complete(self):
        separated_results = separate_results_by_status(self.spawned_agent_results)

        _, failed_results = separated_results

        if len(failed_results) == 0:
            # not do something? maybe ask give options to user:
            # - create new roadmap
            # - quit
            # - maybe user has something to say
            pass

        else:
            formatted_result = format_agents_result(separated_results)
            # missing previous roadmap?
            data = AgentData.from_context(formatted_result)
            context = data.format_conversation()
            self.run_agent_loop(context)

    def run_agent_loop(
        self, problem_query: str
    ) -> Optional[Union[RoadmapCompletionParams, BaseCompletionParams]]:
        logger.debug(f"[{self.agent_type.name}] Starting project planning...")
        print(f"\n[{self.agent_type.name}] Starting project planning...")

        current_query = problem_query
        max_refinement_iterations = 20

        self.run_prerequisites()

        for iteration in range(max_refinement_iterations):
            logger.debug(
                f"Roadmap generation iteration {iteration + 1}/{max_refinement_iterations}"
            )

            result = super().run_agent_loop(current_query)

            # Check if result is BaseCompletionParams instead of RoadmapCompletionParams
            if isinstance(result, BaseCompletionParams):
                logger.debug("Received BaseCompletionParams")
                return None

            # At this point, result must be RoadmapCompletionParams
            if not isinstance(result, RoadmapCompletionParams):
                logger.error(f"Unexpected result type: {type(result)}")
                console.print(
                    "[red]❌ Unexpected response type from agent. Operation cancelled.[/red]"
                )
                return None

            verification_result = verify_roadmap_file_paths(result)
            if not verification_result["valid"]:
                feedback = verification_result["feedback"]
                logger.warning(f"File path verification failed: {feedback[:100]}...")

                self._store_feedback_in_sutra_memory(feedback, result)
                format_feedback_tool_status(feedback)

                if "FILE DOES NOT EXIST" in feedback:
                    current_query = f"{problem_query}\n\nIMPORTANT: The provided file paths for modify or delete operations do not exist. {feedback}"
                else:
                    current_query = (
                        f"{problem_query}\n\nUser feedback for improvement: {feedback}"
                    )

                continue

            logger.debug(f"[{self.agent_type.name}] generated successfully")
            print(f"\n[{self.agent_type.name}] generated successfully")

            user_action = self._get_user_action_on_roadmap()

            if user_action["action"] == "approved":
                logger.debug("User approved roadmap, proceeding with agent spawning")
                self._spawn_agents_based_on_config(result)
                return result

            elif user_action["action"] == "refine":
                feedback = user_action.get("feedback", "")
                if not feedback:
                    logger.warning(
                        "No feedback provided for refinement, treating as cancellation"
                    )
                    console.print(
                        "[yellow]⚠️  No feedback provided. Operation cancelled.[/yellow]"
                    )
                    return None

                logger.debug(f"User requested refinement: {feedback[:100]}...")
                print(
                    f"\n[{self.agent_type.name}] Refining roadmap based on feedback..."
                )

                self._store_feedback_in_sutra_memory(feedback, result)
                format_feedback_tool_status(feedback)

                current_query = (
                    f"{problem_query}\n\nUser feedback for improvement: {feedback}"
                )
                continue

            elif user_action["action"] == "cancelled":
                logger.debug("User cancelled roadmap workflow")
                console.print(
                    "[yellow]⚠️  Roadmap workflow cancelled by user.[/yellow]"
                )
                return None

            else:
                logger.warning(f"Unknown user action: {user_action.get('action')}")
                console.print(
                    "[yellow]⚠️  Unexpected response. Operation cancelled.[/yellow]"
                )
                return None

        logger.warning(
            f"Maximum refinement iterations ({max_refinement_iterations}) reached"
        )
        console.print(
            f"[yellow]⚠️  Maximum refinement attempts reached. Please restart if needed.[/yellow]"
        )
        return None

    def _get_user_action_on_roadmap(self) -> Dict[str, Any]:
        confirmation_text = Text()
        confirmation_text.append("🤔 CONFIRMATION REQUIRED", style="bold yellow")
        confirmation_text.append(
            "\n\nIs this the correct roadmap for your query?\n\n",
            style="white",
        )
        confirmation_text.append("• ", style="green")
        confirmation_text.append("Yes", style="bold green")
        confirmation_text.append(" - Proceed with agent spawning\n", style="white")
        confirmation_text.append("• ", style="red")
        confirmation_text.append("No", style="bold red")
        confirmation_text.append(
            " - Provide feedback to improve the roadmap", style="white"
        )

        confirmation_panel = Panel(
            confirmation_text, border_style="yellow", padding=(1, 2)
        )
        console.print(confirmation_panel)

        try:
            result = Confirm.ask(
                "[bold cyan]👤 Do you want to process this roadmap?[/bold cyan]",
                default=True,
            )

            if result:
                console.print(
                    "\n[bold green]✅ Proceeding with roadmap execution...[/bold green]"
                )
                return {"action": "approved"}
            else:
                console.print(
                    "\n[bold yellow]📝 Please provide feedback to improve the roadmap:[/bold yellow]"
                )

                feedback = Prompt.ask(
                    "[cyan]What would you like to change or improve in this roadmap?[/cyan]",
                    default="",
                )

                if feedback.strip():
                    console.print(
                        "\n[bold yellow]🔄 Refining roadmap with your feedback...[/bold yellow]"
                    )
                    return {"action": "refine", "feedback": feedback.strip()}
                else:
                    console.print(
                        "\n[bold red]❌ No feedback provided. Roadmap execution cancelled.[/bold red]"
                    )
                    return {"action": "cancelled"}

        except KeyboardInterrupt:
            console.print(
                "\n\n[bold red]❌ Operation cancelled by user (Ctrl+C)[/bold red]"
            )
            return {"action": "cancelled"}
        except EOFError:
            console.print("\n\n[bold red]❌ Operation cancelled (EOF)[/bold red]")
            return {"action": "cancelled"}

    def _spawn_agents_based_on_config(
        self, roadmap_result: RoadmapCompletionParams
    ) -> None:
        config = get_config()
        processing_mode = config.agents.roadmap.processing_mode

        logger.debug(f"Roadmap processing mode: {processing_mode}")

        project_prompts = convert_roadmap_to_prompts(roadmap_result.model_dump())

        self.spawned_agent_count = len(project_prompts)

        if not project_prompts:
            logger.warning("No project prompts generated from roadmap")
            console.print("[yellow]⚠️  No projects to process in roadmap.[/yellow]")
            return

        print(
            f"\n[{self.agent_type.name}] Spawning agents for {len(project_prompts)} project(s)"
        )

        if processing_mode == "parallel":
            self._spawn_agents_parallel(project_prompts)
        else:
            self._spawn_agents_sequence(project_prompts)

    def _spawn_agents_sequence(self, project_prompts: list) -> None:
        logger.debug("Spawning agents in sequence mode")

        for i, project_prompt in enumerate(project_prompts, 1):
            project_path_str = project_prompt.get("project_path", "")
            prompt = project_prompt.get("prompt", "")

            print(
                f"\n[{self.agent_type.name}] Processing project {i}/{len(project_prompts)}: {project_path_str}"
            )

            actual_project_dir = (
                Path(project_path_str)
                if Path(project_path_str).is_absolute()
                else Path.cwd() / project_path_str
            )

            logger.debug(
                f"Spawning Developer agent for project at: {actual_project_dir}"
            )

            data = AgentData.from_context(prompt, self.agent_type)
            self.send_to_downstream(data, target_project_path=actual_project_dir)

    def _spawn_agents_parallel(self, project_prompts: list) -> None:
        logger.debug("Spawning agents in parallel mode")

        def process_project(project_prompt: dict) -> None:
            project_path_str = project_prompt.get("project_path", "")
            prompt = project_prompt.get("prompt", "")

            actual_project_dir = (
                Path(project_path_str)
                if Path(project_path_str).is_absolute()
                else Path.cwd() / project_path_str
            )

            logger.debug(
                f"Spawning Developer agent for project at: {actual_project_dir}"
            )

            data = AgentData.from_context(prompt, self.agent_type)
            self.send_to_downstream(data, target_project_path=actual_project_dir)

        with ThreadPoolExecutor(max_workers=len(project_prompts)) as executor:
            futures = [
                executor.submit(process_project, project_prompt)
                for project_prompt in project_prompts
            ]

            for i, future in enumerate(as_completed(futures), 1):
                try:
                    future.result()
                    logger.debug(f"Completed spawning agent {i}/{len(project_prompts)}")
                except Exception as e:
                    logger.error(f"Error spawning agent in parallel: {e}")
                    console.print(f"[red]❌ Error spawning agent: {e}[/red]")

        logger.debug(f"All {len(project_prompts)} agents spawned in parallel")
        print(
            f"\n[{self.agent_type.name}] All {len(project_prompts)} agents spawned in parallel"
        )

    def _store_feedback_in_sutra_memory(
        self, feedback: str, result: RoadmapCompletionParams
    ) -> None:
        try:
            feedback_section = format_feedback_section(feedback, result)
            self.memory.set_feedback_section(feedback_section)
            logger.debug("Stored feedback section in sutra memory")
        except Exception as e:
            logger.error(f"Error storing feedback in sutra memory: {e}")
