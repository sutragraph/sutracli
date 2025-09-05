"""
Specific handlers for different agents' post-requisites.
"""

from typing import Dict, Any
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm
from agent_management.providers.manager import get_agent_provider_manager
from agents_new import Agent
from utils.console import console
from tools import RoadmapCompletionParams


class RoadmapAgentHandler:
    """Handler for roadmap agent post-requisites."""

    def __init__(self):
        self.provider_manager = get_agent_provider_manager()

    def process_agent_result_direct(self, agent_result: Any) -> Dict[str, Any]:
        """Process roadmap agent result directly and trigger post-requisites.

        Expected agent_result format: {"data": {"projects": [ProjectRoadmap], "summary": "..."}}

        Args:
            agent_result: The direct result from roadmap agent

        Returns:
            Dict containing the processing results
        """

        if not isinstance(agent_result, RoadmapCompletionParams):
            return {
                "success": False,
                "error": "No data field found in agent result",
                "processed_actions": [],
            }

        project_prompts = self._convert_roadmap_to_prompts(agent_result.model_dump())

        return self._spawn_external_agents(project_prompts)

    def _convert_roadmap_to_prompts(self, data: Dict[str, Any]) -> list:
        """Convert roadmap data to project prompts format.

        Args:
            data: The roadmap data containing projects and summary

        Returns:
            List of project prompts in the format expected by _spawn_external_agents
        """
        projects = data.get("projects", [])

        project_prompts = []

        for project in projects:
            project_name = project.get("project_name", "")
            project_path = project.get("project_path", "")
            impact_level = project.get("impact_level", "Medium")
            reasoning = project.get("reasoning", "")
            changes = project.get("changes", [])
            contracts = project.get("contracts", [])
            implementation_notes = project.get("implementation_notes", "")

            # Build the prompt string
            prompt_parts = []

            # Add header
            prompt_parts.append(f"# Project Modification Request: {project_name}")
            prompt_parts.append(f"**Project Path:** {project_path}")
            prompt_parts.append(f"**Impact Level:** {impact_level}")
            prompt_parts.append("")

            # Add reasoning
            if reasoning:
                prompt_parts.append("## Reasoning")
                prompt_parts.append(reasoning)
                prompt_parts.append("")

            # Add file changes
            if changes:
                prompt_parts.append("## File Changes Required")
                prompt_parts.append("")

                for i, file_change in enumerate(changes, 1):
                    file_path = file_change.get("file_path", "")
                    operation = file_change.get("operation", "modify")
                    instructions = file_change.get("instructions", [])

                    prompt_parts.append(f"### {i}. File: {file_path}")
                    prompt_parts.append(f"**Operation:** {operation}")
                    prompt_parts.append("")

                    if instructions:
                        prompt_parts.append("**Instructions:**")
                        for j, instruction in enumerate(instructions, 1):
                            description = instruction.get("description", "")
                            current_state = instruction.get("current_state", "")
                            target_state = instruction.get("target_state", "")
                            start_line = instruction.get("start_line")
                            end_line = instruction.get("end_line")
                            additional_notes = instruction.get("additional_notes", "")

                            prompt_parts.append(f"{j}. **Change:** {description}")

                            if current_state:
                                prompt_parts.append(
                                    f"   **Current State:** {current_state}"
                                )

                            if target_state:
                                prompt_parts.append(
                                    f"   **Target State:** {target_state}"
                                )

                            if start_line is not None:
                                if end_line is not None:
                                    prompt_parts.append(
                                        f"   **Lines:** {start_line}-{end_line}"
                                    )
                                else:
                                    prompt_parts.append(f"   **Line:** {start_line}")

                            if additional_notes:
                                prompt_parts.append(f"   **Notes:** {additional_notes}")

                            prompt_parts.append("")

                    prompt_parts.append("")

            # Add contracts
            if contracts:
                prompt_parts.append("## Integration Contracts")
                prompt_parts.append("")
                prompt_parts.append("The following contracts define the interfaces this project must implement or consume:")
                prompt_parts.append("")

                for i, contract in enumerate(contracts, 1):
                    contract_id = contract.get("contract_id", "")
                    contract_type = contract.get("contract_type", "")
                    contract_name = contract.get("name", "")
                    description = contract.get("description", "")
                    interface = contract.get("interface", {})
                    input_format = contract.get("input_format", [])
                    output_format = contract.get("output_format", [])
                    error_codes = contract.get("error_codes", [])
                    examples = contract.get("examples", "")

                    prompt_parts.append(f"### {i}. {contract_name}")
                    prompt_parts.append(f"**Contract ID:** {contract_id}")
                    prompt_parts.append(f"**Type:** {contract_type}")
                    prompt_parts.append("")

                    if description:
                        prompt_parts.append(f"**Description:** {description}")
                        prompt_parts.append("")

                    if interface:
                        prompt_parts.append("**Interface Details:**")
                        for key, value in interface.items():
                            prompt_parts.append(f"- {key}: {value}")
                        prompt_parts.append("")

                    if input_format:
                        prompt_parts.append("**Input Format:**")
                        for field in input_format:
                            field_name = field.get("name", "")
                            field_type = field.get("type", "")
                            required = field.get("required", False)
                            field_description = field.get("description", "")
                            validation_rules = field.get("validation_rules", "")

                            req_text = " (required)" if required else " (optional)"
                            prompt_parts.append(f"- {field_name}: {field_type}{req_text}")

                            if field_description:
                                prompt_parts.append(f"  - {field_description}")
                            if validation_rules:
                                prompt_parts.append(f"  - Validation: {validation_rules}")
                        prompt_parts.append("")

                    if output_format:
                        prompt_parts.append("**Output Format:**")
                        for field in output_format:
                            field_name = field.get("name", "")
                            field_type = field.get("type", "")
                            field_description = field.get("description", "")

                            prompt_parts.append(f"- {field_name}: {field_type}")
                            if field_description:
                                prompt_parts.append(f"  - {field_description}")
                        prompt_parts.append("")

                    if error_codes:
                        prompt_parts.append("**Error Codes:**")
                        for error_code in error_codes:
                            prompt_parts.append(f"- {error_code}")
                        prompt_parts.append("")

                    if examples:
                        prompt_parts.append("**Examples:**")
                        prompt_parts.append(examples)
                        prompt_parts.append("")

                    prompt_parts.append("")

            # Add implementation notes
            if implementation_notes:
                prompt_parts.append("## Implementation Notes")
                prompt_parts.append(implementation_notes)
                prompt_parts.append("")

            # Add final instructions
            prompt_parts.append("## Instructions")
            prompt_parts.append(
                "Please implement the changes described above according to the specifications."
            )
            prompt_parts.append(
                "Ensure that all modifications maintain code quality and follow best practices."
            )

            # Join all parts into a single prompt
            full_prompt = "\n".join(prompt_parts)

            # Create project prompt entry
            project_prompts.append(
                {
                    "prompt": full_prompt,
                    "project_path": project_path,
                }
            )

        return project_prompts

    def _spawn_external_agents(self, project_prompts: list) -> Dict[str, Any]:
        """Spawn external agents for each project with prompts."""
        # Display all generated prompts to the user first
        if not self._get_confirmation(project_prompts):
            return {
                "success": False,
                "error": "User declined to proceed with the roadmap",
                "processed_actions": [],
            }

        # Check if provider is selected, if not prompt user to select one
        selected_provider = self.provider_manager.config_manager.get_selected_provider()

        if not selected_provider:
            print("\n🤖 External Agent Provider Setup Required")
            print("=" * 50)
            print("To process the roadmap results, please select an external agent provider:")

            selected_provider = self.provider_manager.prompt_user_for_provider_selection()
            if not selected_provider:
                return {
                    "success": False,
                    "error": "No external agent provider selected",
                    "processed_actions": []
                }

        # Verify the selected provider is available
        provider = self.provider_manager.get_provider(selected_provider)
        if not provider or not provider.is_available():
            print(f"\n❌ Selected provider '{selected_provider}' is not available.")
            print("Please ensure the CLI tool is installed and accessible.")

            # Prompt for new selection
            print("\nPlease select an available provider:")
            new_provider = self.provider_manager.prompt_user_for_provider_selection()
            if not new_provider:
                return {
                    "success": False,
                    "error": f"Selected provider '{selected_provider}' is not available",
                    "processed_actions": []
                }
            selected_provider = new_provider

        # Process each project prompt in parallel
        print(f"\n🚀 Spawning {len(project_prompts)} external agents in parallel...")
        print("⚡ All terminals will be created simultaneously")

        # Execute all prompts in parallel
        spawn_results = self.provider_manager.execute_multiple_prompts_parallel(
            project_prompts
        )

        # Determine overall success
        successful_spawns = sum(1 for result in spawn_results if result["success"])
        total_spawns = len(spawn_results)

        return {
            "success": successful_spawns > 0,
            "message": f"Successfully spawned {successful_spawns}/{total_spawns} external agents",
            "processed_actions": [{
                "action": "spawn_external_agents",
                "success": successful_spawns > 0,
                "message": f"Spawned {successful_spawns}/{total_spawns} agents",
                "details": {
                    "total_projects": total_spawns,
                    "successful_spawns": successful_spawns,
                    "failed_spawns": total_spawns - successful_spawns,
                    "results": spawn_results
                }
            }]
        }

    def _get_confirmation(self, project_prompts: list) -> bool:
        """Display all generated prompts to the user and get confirmation to proceed.

        Args:
            project_prompts: List of project prompts with prompt

        Returns:
            bool: True if user wants to continue, False otherwise
        """
        # Create confirmation panel
        confirmation_text = Text()
        confirmation_text.append("🤔 CONFIRMATION REQUIRED", style="bold yellow")
        confirmation_text.append(
            "\n\nDo you want to continue with this roadmap and spawn external agents?\n\n",
            style="white",
        )
        confirmation_text.append("• ", style="green")
        confirmation_text.append("Yes", style="bold green")
        confirmation_text.append(" - Proceed with agent spawning\n", style="white")
        confirmation_text.append("• ", style="red")
        confirmation_text.append("No", style="bold red")
        confirmation_text.append(" - Cancel and stop the process", style="white")

        confirmation_panel = Panel(
            confirmation_text, border_style="yellow", padding=(1, 2)
        )
        console.print(confirmation_panel)

        # Use Rich's Confirm for user input
        try:
            result = Confirm.ask(
                "[bold cyan]👤 Do you want to proceed with this roadmap?[/bold cyan]",
                default=True,
            )

            if result:
                console.print(
                    "\n[bold green]✅ Proceeding with roadmap execution...[/bold green]"
                )
                return True
            else:
                console.print(
                    "\n[bold red]❌ Roadmap execution cancelled by user.[/bold red]"
                )
                return False

        except KeyboardInterrupt:
            console.print(
                "\n\n[bold red]❌ Operation cancelled by user (Ctrl+C)[/bold red]"
            )
            return False
        except EOFError:
            console.print("\n\n[bold red]❌ Operation cancelled (EOF)[/bold red]")
            return False


class BaseAgentHandler:
    """Base class for agent handlers."""

    def __init__(self, agent_key: Agent):
        self.agent_key = agent_key

    def process_agent_result_direct(self, agent_result: Any) -> Dict[str, Any]:
        """Process agent result directly - default implementation."""
        return {
            "success": True,
            "message": f"No post-requisites configured for agent: {self.agent_key}",
            "processed_actions": []
        }


# Factory function to get appropriate handler
def get_agent_handler(agent_key: Agent):
    """Get the appropriate handler for an agent."""
    if agent_key == Agent.ROADMAP:
        return RoadmapAgentHandler()
    else:
        return BaseAgentHandler(agent_key)
