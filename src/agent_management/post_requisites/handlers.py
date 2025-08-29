"""
Specific handlers for different agents' post-requisites.
"""

from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm
from rich.markdown import Markdown
from ..providers.manager import get_agent_provider_manager


class RoadmapAgentHandler:
    """Handler for roadmap agent post-requisites."""

    def __init__(self):
        self.provider_manager = get_agent_provider_manager()
        self.console = Console()

    def process_agent_result_direct(self, agent_result: Any) -> Dict[str, Any]:
        """Process roadmap agent result directly and trigger post-requisites.
        
        Expected agent_result format: [{"project_id": "123", "prompt": "some prompt"}, ...]
        
        Args:
            agent_result: The direct result from roadmap agent
            
        Returns:
            Dict containing the processing results
        """
        if not agent_result:
            return {
                "success": False,
                "error": "No agent result provided",
                "processed_actions": []
            }

        # Validate the result format
        if not self.validate_roadmap_result(agent_result):
            return {
                "success": False,
                "error": "Invalid roadmap result format. Expected: [{'project_id': 'id', 'prompt': 'text'}, ...]",
                "processed_actions": []
            }

        # Process the roadmap results - spawn external agents
        return self._spawn_external_agents(agent_result)

    def validate_roadmap_result(self, result_data: Any) -> bool:
        """Validate that the roadmap result has the expected format.
        
        Expected format: [{"project_id": "123", "prompt": "some prompt"}, ...]
        """
        if not isinstance(result_data, list):
            return False

        for item in result_data:
            if not isinstance(item, dict):
                return False

            if "project_id" not in item or "prompt" not in item:
                return False

            if not isinstance(item["project_id"], (str, int)) or not isinstance(item["prompt"], str):
                return False

        return True

    def _spawn_external_agents(self, project_prompts: list) -> Dict[str, Any]:
        """Spawn external agents for each project with prompts."""
        # Display all generated prompts to the user first
        if not self._display_prompts_and_get_confirmation(project_prompts):
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

        # Process each project prompt
        spawn_results = []
        for project_prompt in project_prompts:
            project_id = project_prompt.get("project_id")
            prompt = project_prompt.get("prompt")

            if not project_id or not prompt:
                spawn_results.append({
                    "project_id": project_id,
                    "success": False,
                    "error": "Missing project_id or prompt"
                })
                continue

            # Get project path from database
            project_path = self._get_project_path(project_id)
            if not project_path:
                spawn_results.append({
                    "project_id": project_id,
                    "success": False,
                    "error": f"Project not found in database: {project_id}"
                })
                continue

            # Execute prompt with selected provider
            execution_result = self.provider_manager.execute_prompt_with_selected_provider(
                project_path, prompt
            )

            spawn_results.append({
                "project_id": project_id,
                "project_path": project_path,
                "prompt": prompt,
                "success": execution_result.get("success", False),
                "output": execution_result.get("output", ""),
                "error": execution_result.get("error", "")
            })

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

    def _get_project_path(self, project_id: str) -> Optional[str]:
        """Get project path from database by project ID."""
        try:
            from src.graph.sqlite_client import SQLiteConnection

            # Convert project_id to int if it's a string
            if isinstance(project_id, str):
                project_id = int(project_id)

            # Query database for project
            db_client = SQLiteConnection()
            query = "SELECT path FROM projects WHERE id = ?"
            result = db_client.execute_query(query, (project_id,))

            if result and len(result) > 0:
                return result[0][0]  # Return the path

            return None

        except (ValueError, Exception) as e:
            print(f"Error getting project path for ID {project_id}: {e}")
            return None

    def _display_prompts_and_get_confirmation(self, project_prompts: list) -> bool:
        """Display all generated prompts to the user and get confirmation to proceed.

        Args:
            project_prompts: List of project prompts with project_id and prompt

        Returns:
            bool: True if user wants to continue, False otherwise
        """
        # Create main header panel
        header_text = Text()
        header_text.append("🗺️  ROADMAP AGENT", style="bold blue")
        header_text.append(" - ", style="white")
        header_text.append("GENERATED PROMPTS REVIEW", style="bold yellow")

        header_panel = Panel(header_text, border_style="bright_blue", padding=(1, 2))
        self.console.print(header_panel)

        # Summary information
        summary_text = f"The roadmap agent has generated [bold green]{len(project_prompts)}[/bold green] prompt(s) for external agents.\n"
        summary_text += "[dim]Please review the prompts below before proceeding:[/dim]"
        self.console.print(summary_text)
        self.console.print()

        # Display each prompt in a beautiful panel
        for i, project_prompt in enumerate(project_prompts, 1):
            project_id = project_prompt.get("project_id", "Unknown")
            prompt_content = project_prompt.get("prompt", "No prompt available")

            # Get project path for display
            project_path = self._get_project_path(project_id)
            project_display = (
                f"{project_path} (ID: {project_id})"
                if project_path
                else f"Project ID: {project_id}"
            )

            # Create prompt header
            prompt_header = Text()
            prompt_header.append(
                f"📋 PROMPT {i}/{len(project_prompts)}", style="bold cyan"
            )
            prompt_header.append(f"\n📁 Project: ", style="dim")
            prompt_header.append(project_display, style="green")

            # Create prompt content with syntax highlighting if it looks like code
            if "**File:" in prompt_content and "**Steps**:" in prompt_content:
                # This looks like a structured prompt, render as markdown
                prompt_display = Markdown(prompt_content)
            else:
                # Plain text prompt
                prompt_display = Text(prompt_content, style="white")

            # Create the prompt panel
            prompt_panel = Panel(
                prompt_display,
                title=prompt_header,
                title_align="left",
                border_style="cyan",
                padding=(1, 2),
            )

            self.console.print(prompt_panel)
            self.console.print()

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
        self.console.print(confirmation_panel)

        # Use Rich's Confirm for user input
        try:
            result = Confirm.ask(
                "[bold cyan]👤 Do you want to proceed with this roadmap?[/bold cyan]",
                default=False,
                console=self.console,
            )

            if result:
                self.console.print(
                    "\n[bold green]✅ Proceeding with roadmap execution...[/bold green]"
                )
                return True
            else:
                self.console.print(
                    "\n[bold red]❌ Roadmap execution cancelled by user.[/bold red]"
                )
                return False

        except KeyboardInterrupt:
            self.console.print(
                "\n\n[bold red]❌ Operation cancelled by user (Ctrl+C)[/bold red]"
            )
            return False
        except EOFError:
            self.console.print("\n\n[bold red]❌ Operation cancelled (EOF)[/bold red]")
            return False


class BaseAgentHandler:
    """Base class for agent handlers."""
    
    def __init__(self, agent_key: str):
        self.agent_key = agent_key
    
    def process_agent_result_direct(self, agent_result: Any) -> Dict[str, Any]:
        """Process agent result directly - default implementation."""
        return {
            "success": True,
            "message": f"No post-requisites configured for agent: {self.agent_key}",
            "processed_actions": []
        }


# Factory function to get appropriate handler
def get_agent_handler(agent_key: str):
    """Get the appropriate handler for an agent."""
    if agent_key == "roadmap":
        return RoadmapAgentHandler()
    else:
        return BaseAgentHandler(agent_key)
