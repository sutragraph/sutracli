"""
Specific handlers for different agents' post-requisites.
"""

from typing import Dict, Any
import os
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm
from agent_management.providers.manager import get_agent_provider_manager
from agents_new import Agent
from utils.console import console
from tools import RoadmapCompletionParams
from loguru import logger


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
        logger.debug("Converting roadmap data to project prompts...")
        projects = data.get("projects", [])

        # Ensure projects is a list and not None
        if projects is None:
            projects = []

        project_prompts = []

        for project in projects:
            project_name = project.get("project_name", "")
            project_path = project.get("project_path", "")
            impact_level = project.get("impact_level", "Medium")
            reasoning = project.get("reasoning", "")
            changes = project.get("changes", [])
            contracts = project.get("contracts", [])
            implementation_plan = project.get("implementation_plan", [])

            # Build the prompt string
            prompt_parts = []

            # Add header
            prompt_parts.append(f"# Project Modification Request: {project_name}")
            prompt_parts.append(f"Project Path: {project_path}")
            prompt_parts.append(f"Impact Level: {impact_level}")
            prompt_parts.append("")

            # Add reasoning
            if reasoning:
                prompt_parts.append("## Reasoning")
                prompt_parts.append(str(reasoning))
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
                    prompt_parts.append(f"Operation: {operation}")
                    prompt_parts.append("")

                    if instructions:
                        prompt_parts.append("Instructions:")
                        for j, instruction in enumerate(instructions, 1):
                            description = instruction.get("description", "")
                            current_state = instruction.get("current_state", "")
                            target_state = instruction.get("target_state", "")
                            start_line = instruction.get("start_line")
                            end_line = instruction.get("end_line")
                            additional_notes = instruction.get("additional_notes", "")

                            prompt_parts.append(f"{j}. Change: {str(description)}")

                            if current_state:
                                prompt_parts.append(
                                    f"   Current State: {str(current_state)}"
                                )

                            if target_state:
                                prompt_parts.append(
                                    f"   Target State: {str(target_state)}"
                                )

                            if start_line is not None:
                                if end_line is not None:
                                    prompt_parts.append(
                                        f"   Lines: {start_line}-{end_line}"
                                    )
                                else:
                                    prompt_parts.append(f"   Line: {start_line}")

                            if additional_notes:
                                prompt_parts.append(
                                    f"   Notes: {str(additional_notes)}"
                                )

                            prompt_parts.append("")

                    prompt_parts.append("")

            # Add contracts
            if contracts:
                prompt_parts.append("## Integration Contracts")
                prompt_parts.append("")
                prompt_parts.append(
                    "The following contracts define the interfaces this project must implement or consume:")
                prompt_parts.append("")

                for i, contract in enumerate(contracts, 1):
                    contract_id = contract.get("contract_id", "")
                    contract_type = contract.get("contract_type", "")
                    contract_name = contract.get("name", "")
                    description = contract.get("description", "")
                    role = contract.get("role", "")
                    interface = contract.get("interface", {})
                    input_format = contract.get("input_format", [])
                    output_format = contract.get("output_format", [])
                    error_codes = contract.get("error_codes", [])
                    authentication_required = contract.get("authentication_required", False)
                    examples = contract.get("examples", "")
                    instructions_contract = contract.get("instructions", "")

                    prompt_parts.append(f"### {i}. {contract_name}")
                    prompt_parts.append(f"Contract ID: {contract_id}")
                    prompt_parts.append(f"Type: {contract_type}")

                    if role:
                        if role == "provider":
                            role_desc = "Implements this contract"
                        elif role == "consumer":
                            role_desc = "Consumes this contract"
                        elif role == "both":
                            role_desc = "Acts as both provider and consumer for this contract (proxy/intermediary)"
                        else:
                            role_desc = f"Role: {role}"
                        prompt_parts.append(f"Role: {role} ({role_desc})")

                    prompt_parts.append("")

                    if description:
                        prompt_parts.append(f"Description: {str(description)}")
                        prompt_parts.append("")

                    if interface:
                        prompt_parts.append("Interface Details:")
                        for key, value in interface.items():
                            prompt_parts.append(f"- {key}: {value}")
                        prompt_parts.append("")

                    # Define a helper function to process nested fields recursively
                    def _process_level(fields, indent_level=0):
                        # Determine the indentation and bullet style based on the current depth
                        indent = "  " * indent_level
                        bullet = "•" if indent_level > 0 else "-"

                        for field in fields:
                            # Safely get all field attributes
                            name = field.get("name", "N/A")
                            field_type = field.get("type", "N/A")
                            description = field.get("description")
                            validation = field.get("validation")
                            nested_fields = field.get("nested")

                            # Format the 'required' text only if the key is present
                            req_text = ""
                            if 'required' in field:
                                req_text = " (required)" if field['required'] else " (optional)"

                            # 1. Add the main line for the current field
                            prompt_parts.append(
                                f"{indent}{bullet} {name}: `{field_type}`{req_text}"
                            )

                            # 2. Add sub-details like description and validation
                            sub_indent = indent + "  "
                            if description:
                                prompt_parts.append(
                                    f"{sub_indent}Description: {description}"
                                )
                            if validation:
                                prompt_parts.append(
                                    f"{sub_indent}Validation: `{validation}`"
                                )

                            # 3. If there are nested fields, call this function again with an increased indent
                            if nested_fields:
                                _process_level(nested_fields, indent_level + 1)

                    if input_format:
                        prompt_parts.append("Input Format:")
                        _process_level(input_format)
                        prompt_parts.append("")

                    if output_format:
                        prompt_parts.append("Output Format:")
                        _process_level(output_format)
                        prompt_parts.append("")

                    if error_codes:
                        prompt_parts.append("Error Codes:")
                        for error_code in error_codes:
                            prompt_parts.append(f"- {error_code}")
                        prompt_parts.append("")

                    if authentication_required:
                        prompt_parts.append("Authentication: Required")
                        prompt_parts.append("")

                    if examples:
                        prompt_parts.append("Examples:")
                        prompt_parts.append("```")
                        prompt_parts.append(str(examples))
                        prompt_parts.append("```")
                        prompt_parts.append("")

                    if instructions_contract:
                        prompt_parts.append(
                            f"Implementation Notes: {str(instructions_contract)}"
                        )
                        prompt_parts.append("")

                    prompt_parts.append("")

            # Add implementation notes
            if len(implementation_plan):
                prompt_parts.append("## Implementation Plan")
                prompt_parts.append("")
                for item in implementation_plan:
                    prompt_parts.append(f"- {item}")
                prompt_parts.append("")

            # Add final instructions
            prompt_parts.append("## Instructions")
            prompt_parts.append(
                "Please implement the changes described above according to the specifications."
            )
            prompt_parts.append(
                "Ensure that all modifications maintain code quality and follow best practices."
            )
            prompt_parts.append(
                "For contracts marked as 'provider', implement the interface. For contracts marked as 'consumer', integrate with the existing interface."
            )

            # Add the important consistency instruction
            prompt_parts.append("")
            prompt_parts.append(
                "Important: Maintain strict naming consistency - use the exact same function names, API endpoints, contract identifiers, variable names, and method signatures as specified in the original query and requirements above."
            )

            # Join all parts into a single prompt - ensure all items are strings
            def flatten_to_strings(items):
                """Recursively flatten any nested structures to strings."""
                result = []
                for item in items:
                    if isinstance(item, list):
                        # Recursively flatten nested lists
                        result.extend(flatten_to_strings(item))
                    elif isinstance(item, (dict, tuple)):
                        # Convert complex types to string representation
                        result.append(str(item))
                    else:
                        # Convert to string if it's not already
                        result.append(str(item))
                return result

            string_parts = flatten_to_strings(prompt_parts)
            full_prompt = "\n".join(string_parts)

            # Create project prompt entry
            project_prompts.append(
                {
                    "prompt": full_prompt,
                    "project_path": project_path,
                }
            )

        return project_prompts

    def _verify_file_paths(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that file paths for modify and delete operations exist.

        Args:
            data: The roadmap data containing projects

        Returns:
            Dict with 'valid' (bool) and 'feedback' (str) if validation fails
        """
        logger.debug("Verifying file paths for modify and delete operations...")
        projects = data.get("projects", [])
        non_existing_paths = []

        for project in projects:
            project_path = project.get("project_path", "")
            changes = project.get("changes", [])

            # Get the project root directory for file checking
            # First try to find the project root from current working directory
            current_dir = os.getcwd()
            project_root = self._find_project_root(current_dir, project_path)

            for change in changes:
                operation = change.get("operation", "")
                file_path = change.get("file_path", "")

                # Only check modify and delete operations
                # Handle both string and enum values - convert to lowercase string
                operation_str = operation
                if hasattr(operation, "value"):
                    operation_str = operation.value
                operation_str = str(operation_str).lower()

                if operation_str in ["modify", "delete"]:
                    # Construct full file path
                    if project_root:
                        full_file_path = os.path.join(project_root, file_path)
                    else:
                        # Fallback to original logic if project root not found
                        clean_project_path = (
                            project_path[1:]
                            if project_path.startswith("/")
                            else project_path
                        )
                        full_file_path = os.path.join(clean_project_path, file_path)

                    # Check if file exists
                    if not os.path.exists(full_file_path):
                        non_existing_paths.append(
                            {
                                "project": project.get("project_name", "Unknown"),
                                "project_path": project_path,
                                "file_path": file_path,
                                "operation": operation,
                                "full_path": full_file_path,
                            }
                        )
                    else:
                        logger.debug(f"File exists and verified: {full_file_path}")

        if non_existing_paths:
            # Create feedback message for non-existing paths
            feedback_message = "The following file paths provided for modify or delete operations do not exist:\n\n"

            for i, path_info in enumerate(non_existing_paths, 1):
                feedback_message += f"{i}. Project: {path_info['project']}\n"
                feedback_message += f"   Operation: {path_info['operation']}\n"
                feedback_message += f"   File path: {path_info['file_path']}\n"
                feedback_message += f"   Full path: {path_info['full_path']}\n"
                feedback_message += f"   Status: FILE DOES NOT EXIST\n\n"

            feedback_message += "Please provide correct file paths that exist in the project before proceeding with any modification or deletion operations. "
            feedback_message += "Make sure to verify the file paths are correct and the files actually exist in the specified locations."

            return {
                "valid": False,
                "feedback": feedback_message,
                "non_existing_paths": non_existing_paths,
            }

        return {"valid": True}

    def _find_project_root(self, current_dir: str, project_path: str) -> str:
        """Find the actual project root directory for file verification.

        Args:
            current_dir: Current working directory
            project_path: Project path from roadmap data

        Returns:
            Absolute path to project root or None if not found
        """
        try:
            # Case 1: project_path is already an absolute path
            if os.path.isabs(project_path):
                if os.path.exists(project_path) and os.path.isdir(project_path):
                    return project_path
                else:
                    logger.debug(
                        f"Absolute project path does not exist: {project_path}"
                    )
                    return None

            # Remove leading slash from project_path if present for relative path handling
            clean_project_path = (
                project_path[1:] if project_path.startswith("/") else project_path
            )

            # Case 2: project_path is relative to current directory
            potential_root = os.path.join(current_dir, clean_project_path)
            if os.path.exists(potential_root) and os.path.isdir(potential_root):
                return potential_root

            # Case 3: we are already in the project directory
            if os.path.basename(current_dir) == clean_project_path.split("/")[-1]:
                return current_dir

            # Case 4: project_path matches a subdirectory in current directory
            project_name = clean_project_path.split("/")[-1]
            potential_root = os.path.join(current_dir, project_name)
            if os.path.exists(potential_root) and os.path.isdir(potential_root):
                return potential_root

            # Case 5: Look for the project in parent directories
            parent_dir = os.path.dirname(current_dir)
            if parent_dir != current_dir:  # Avoid infinite loop at filesystem root
                potential_root = os.path.join(parent_dir, clean_project_path)
                if os.path.exists(potential_root) and os.path.isdir(potential_root):
                    return potential_root

            logger.debug(f"Could not find project root for: {project_path}")
            return None

        except Exception as e:
            logger.error(f"Error finding project root: {e}")
            return None

    def _spawn_external_agents(self, project_prompts: list) -> Dict[str, Any]:
        """Spawn external agents for each project with prompts."""
        # Display all generated prompts to the user first
        confirmation_result = self._get_confirmation()

        if not confirmation_result["proceed"]:
            # Check if user provided feedback for improvement
            if "feedback" in confirmation_result:
                return {
                    "success": False,
                    "error": "User requested roadmap improvement",
                    "feedback": confirmation_result["feedback"],
                    "continue_roadmap": True,
                    "processed_actions": [],
                }
            else:
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

    def _get_confirmation(self) -> Dict[str, Any]:
        """Display final confirmation when all file paths are verified and correct.

        Returns:
            Dict: Contains 'proceed' (bool) and optionally 'feedback' (str) for improvement
        """
        # Create confirmation panel
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
        # Use Rich's Confirm for user input
        try:
            result = Confirm.ask(
                "[bold cyan]👤 Do you want to process this roadmap?[/bold cyan]",
                default=True,
            )

            if result:
                console.print(
                    "\n[bold green]✅ Proceeding with roadmap execution...[/bold green]"
                )
                return {"proceed": True}
            else:
                # Ask for user feedback instead of cancelling
                console.print(
                    "\n[bold yellow]📝 Please provide feedback to improve the roadmap:[/bold yellow]"
                )

                from rich.prompt import Prompt

                feedback = Prompt.ask(
                    "[cyan]What would you like to change or improve in this roadmap?[/cyan]",
                    default="",
                )

                if feedback.strip():
                    console.print(
                        "\n[bold yellow]🔄 Continuing roadmap agent loop with your feedback...[/bold yellow]"
                    )
                    return {"proceed": False, "feedback": feedback.strip()}
                else:
                    console.print(
                        "\n[bold red]❌ No feedback provided. Roadmap execution cancelled.[/bold red]"
                    )
                    return {"proceed": False}

        except KeyboardInterrupt:
            console.print(
                "\n\n[bold red]❌ Operation cancelled by user (Ctrl+C)[/bold red]"
            )
            return {"proceed": False}
        except EOFError:
            console.print("\n\n[bold red]❌ Operation cancelled (EOF)[/bold red]")
            return {"proceed": False}


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
