#!/usr/bin/env python3
"""
Modern CLI for SutraGraph - Interactive command-line interface with provider setup and agent management.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.align import Align

# Prompt toolkit imports for arrow key navigation
from prompt_toolkit import Application, prompt
from prompt_toolkit.layout import Layout, HSplit
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from src.agents_new import Agent
from src.utils.console import console
from src.config.settings import reload_config
from src.agent_management.prerequisites.agent_config import (
    get_agent_registry,
)

from src.utils.logging import setup_logging


class UserCancelledError(Exception):
    """Exception raised when user cancels an operation."""

    pass


class ModernSutraKit:
    """Modern interactive CLI for SutraGraph."""

    def __init__(self, log_level: str = "INFO"):
        """Initialize the modern CLI."""
        self.config_path = Path.home() / ".sutra" / "config" / "system.json"
        self.agent_registry = get_agent_registry()
        self.log_level = log_level

        # Setup logging with the specified level (default: INFO)
        setup_logging(log_level)

    def print_banner(self):
        """Print the welcome banner."""
        banner = """
    ███████╗██╗   ██╗████████╗██████╗  █████╗    ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗
    ██╔════╝██║   ██║╚══██╔══╝██╔══██╗██╔══██╗  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║
    ███████╗██║   ██║   ██║   ██████╔╝███████║  ██║  ███╗██████╔╝███████║██████╔╝███████║
    ╚════██║██║   ██║   ██║   ██╔══██╗██╔══██║  ██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║
    ███████║╚██████╔╝   ██║   ██║  ██║██║  ██║  ╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║
    ╚══════╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
        """

        panel = Panel(
            Align.center(Text(banner, style="bold blue")),
            title="🚀 Welcome to SutraGraph",
            subtitle="AI-Powered Code Analysis & Automation",
            border_style="bright_blue"
        )
        console.print(panel)

    def check_llm_provider_configured(self) -> bool:
        """Check if LLM provider is already configured."""
        try:
            if not self.config_path.exists():
                return False

            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

            llm_config = config_data.get('llm', {})
            provider = llm_config.get('provider')

            if not provider:
                return False

            # Check if provider-specific config exists
            provider_config = llm_config.get(provider, {})
            if not provider_config:
                return False

            # Basic validation for each provider
            if provider == 'aws':
                required_fields = ['access_key_id', 'secret_access_key', 'model_id', 'region']
                return all(provider_config.get(field) for field in required_fields)
            elif provider == 'anthropic':
                return bool(provider_config.get('api_key') and provider_config.get('model_id'))
            elif provider == 'gcp':
                required_fields = ['api_key', 'project_id', 'location']
                return all(provider_config.get(field) for field in required_fields)
            elif provider == 'openai':
                return bool(provider_config.get('api_key') and provider_config.get('model_id'))

            return True

        except Exception:
            return False

    def setup_llm_provider(self):
        """Interactive LLM provider setup with arrow keys."""
        console.info("LLM Provider Setup")

        providers = [
            {"name": "Anthropic (Claude)", "key": "anthropic",
             "description": "Claude models (claude-3.5-sonnet, etc.)"},
            {"name": "AWS Bedrock", "key": "aws", "description": "AWS managed AI services"},
            {"name": "Google Gemini", "key": "gcp", "description": "Google's Gemini models"},
            {"name": "OpenAI (ChatGPT)", "key": "openai", "description": "GPT models via OpenAI API"}
        ]

        table = Table()
        table.add_column("Provider", style="green")
        table.add_column("Description", style="white")

        for provider in providers:
            table.add_row(provider["name"], provider["description"])

        console.print(table)
        console.print()

        selected_provider = self._arrow_key_select_provider(providers)
        if not selected_provider:
            console.error("No provider selected. Exiting.")
            sys.exit(1)

        provider_key = selected_provider["key"]
        console.success(f"Selected: {selected_provider['name']}")

        # Collect provider-specific configuration
        config_data = self._get_provider_config(provider_key)

        # Update only the LLM configuration
        updated_config = self._update_llm_config(provider_key, config_data)

        # Save configuration
        self._save_config(updated_config)

        console.success("Configuration saved successfully!")

    def _get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for specific provider."""
        if provider == "aws":
            return self._get_aws_config()
        elif provider == "anthropic":
            return self._get_anthropic_config()
        elif provider == "gcp":
            return self._get_gcp_config()
        elif provider == "openai":
            return self._get_openai_config()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _get_aws_config(self) -> Dict[str, Any]:
        """Get AWS Bedrock configuration."""
        console.info("AWS Bedrock Configuration")
        access_key = Prompt.ask("AWS Access Key ID", password=False)
        secret_key = prompt("AWS Secret Access Key: ", is_password=True)
        region = Prompt.ask("AWS Region", default="us-east-2")
        model_id = Prompt.ask("Model ID", default="us.anthropic.claude-sonnet-4-20250514-v1:0")

        return {
            "access_key_id": access_key,
            "secret_access_key": secret_key,
            "region": region,
            "model_id": model_id
        }

    def _get_anthropic_config(self) -> Dict[str, Any]:
        """Get Anthropic configuration."""
        console.info("Anthropic Configuration")
        api_key = prompt("Anthropic API Key: ", is_password=True)
        model_id = Prompt.ask("Model ID", default="claude-3-5-sonnet-20241022")

        return {
            "api_key": api_key,
            "model_id": model_id
        }

    def _get_gcp_config(self) -> Dict[str, Any]:
        """Get Google Cloud configuration."""
        console.info("Google Cloud Configuration")
        api_key = prompt("Google API Key: ", is_password=True)
        project_id = Prompt.ask("Project ID")
        location = Prompt.ask("Location", default="us-central1")
        llm_endpoint = Prompt.ask("LLM Endpoint", default="")

        return {
            "api_key": api_key,
            "project_id": project_id,
            "location": location,
            "llm_endpoint": llm_endpoint
        }

    def _get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration."""
        console.info("OpenAI Configuration")
        api_key = prompt("OpenAI API Key: ", is_password=True)
        model_id = Prompt.ask("Model ID", default="gpt-4o")

        return {
            "api_key": api_key,
            "model_id": model_id
        }

    def _load_existing_config(self) -> Dict[str, Any]:
        """Load existing configuration or exit if not found."""
        if not self.config_path.exists():
            console.error("Configuration file not found. Did you run the 'sutrakit-setup' command?")
            console.info("Please run 'sutrakit-setup' first to initialize the system configuration.")
            sys.exit(1)

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            console.error(f"Invalid JSON in configuration file: {e}")
            console.error("Configuration file appears to be corrupted. Please run 'sutrakit-setup' again.")
            sys.exit(1)
        except Exception as e:
            console.error(f"Error reading configuration file: {e}")
            sys.exit(1)

    def _update_llm_config(self, provider: str, provider_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update only the LLM configuration, preserving other settings."""
        # Load existing configuration (will exit if not found)
        existing_config = self._load_existing_config()

        existing_config["llm"]["provider"] = provider

        existing_config["llm"][provider] = provider_config

        return existing_config

    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Reload the configuration to update the in-memory instance
        reload_config()

    def select_agent(self) -> Agent:
        """Interactive agent selection with arrow keys."""
        available_agents = self.agent_registry.get_available_agents()

        console.info("Agent Selection")

        # Show available agents table
        if available_agents:
            table = Table()
            table.add_column("Agent", style="green")
            table.add_column("Description", style="white")

            for agent in available_agents:
                table.add_row(agent.name, agent.description)

            console.print(table)

        console.print()

        if not available_agents:
            console.error("No agents available")
            return Agent.ROADMAP

        # Use arrow key selection
        selected_agent = self._arrow_key_select_agents(available_agents)
        if selected_agent:
            return selected_agent.key
        else:
            console.error("No agent selected. Exiting.")
            sys.exit(1)

    def _arrow_key_select_provider(self, providers):
        """Arrow key selection for LLM providers."""
        current_index = 0

        def get_formatted_text():
            lines = [('', 'Select LLM provider (↑↓ to navigate, Enter to select, Esc to cancel):\n\n')]

            for i, provider in enumerate(providers):
                if i == current_index:
                    lines.append(('class:selected', f'▶ {provider["name"]}\n'))
                else:
                    lines.append(('', f'  {provider["name"]}\n'))

            return lines

        # Key bindings
        bindings = KeyBindings()

        @bindings.add('up')
        def move_up(event):
            nonlocal current_index
            current_index = (current_index - 1) % len(providers)

        @bindings.add('down')
        def move_down(event):
            nonlocal current_index
            current_index = (current_index + 1) % len(providers)

        @bindings.add('enter')
        def select_item(event):
            event.app.exit(result=providers[current_index])

        @bindings.add('escape')
        @bindings.add('c-c')
        def cancel(event):
            event.app.exit(result=None)

        # Create the application
        application = Application(
            layout=Layout(
                HSplit([
                    Window(FormattedTextControl(get_formatted_text), wrap_lines=True),
                ])
            ),
            key_bindings=bindings,
            mouse_support=False,
            full_screen=False,
            style=Style([
                ('selected', 'bg:#0066cc #ffffff bold'),
                ('dim', '#666666'),
            ])
        )

        # Run the application
        return application.run()

    def _arrow_key_select_agents(self, agents):
        """Custom arrow key selection for agents."""
        current_index = 0

        def get_formatted_text():
            lines = [('', 'Select agent (↑↓ to navigate, Enter to select, Esc to cancel):\n\n')]

            for i, agent in enumerate(agents):
                if i == current_index:
                    lines.append(('class:selected', f'▶ {agent.name}'))
                else:
                    lines.append(('', f'  {agent.name}'))

            return lines

        # Key bindings
        bindings = KeyBindings()

        @bindings.add('up')
        def move_up(event):
            nonlocal current_index
            current_index = (current_index - 1) % len(agents)

        @bindings.add('down')
        def move_down(event):
            nonlocal current_index
            current_index = (current_index + 1) % len(agents)

        @bindings.add('enter')
        def select_item(event):
            event.app.exit(result=agents[current_index])

        @bindings.add('escape')
        @bindings.add('c-c')
        def cancel(event):
            event.app.exit(result=None)

        # Create the application
        application = Application(
            layout=Layout(
                HSplit([
                    Window(FormattedTextControl(get_formatted_text), wrap_lines=True),
                ])
            ),
            key_bindings=bindings,
            mouse_support=False,
            full_screen=False,
            style=Style([
                ('selected', 'bg:#0066cc #ffffff bold'),
                ('dim', '#666666'),
            ])
        )

        # Run the application
        return application.run()

    def show_agent_prerequisites(self, agent_enum: Agent):
        """Show prerequisites for selected agent."""
        agent_config = self.agent_registry.get_agent(agent_enum)
        if not agent_config:
            return

        console.success(f"Selected: {agent_config.name}")
        console.dim(agent_config.description)

        table = Table(show_header=False, box=None)
        table.add_column("Status", style="", width=3)
        table.add_column("Requirement", style="")
        table.add_column("Description", style="dim")

        console.print(table)
        console.print()

    def run_agent_workflow(self, agent_enum: Agent, current_dir: Path):
        """Run the workflow for selected agent."""
        agent_config = self.agent_registry.get_agent(agent_enum)
        if not agent_config:
            console.error(f"Agent '{agent_enum}' not found.")
            return

        # Check if agent is available (implemented)
        available_agents = self.agent_registry.get_available_agents()
        if agent_config not in available_agents:
            console.warning(f"Agent '{agent_config.name}' is not yet implemented.")
            return

        try:
            # Check if indexing is required
            if agent_config.requires_indexing:
                self._run_indexing(current_dir)

            # Check if cross-indexing is required
            if agent_config.requires_cross_indexing:
                self._run_cross_indexing(current_dir)

            # Run the actual agent
            if agent_enum.value == "ROADMAP":
                self._execute_agent(current_dir, agent_enum, agent_config)
            else:
                console.error(f"Agent '{agent_enum}' not implemented yet.")

        except UserCancelledError:
            console.warning("Workflow stopped by user choice.")
            console.dim("You can restart the workflow anytime when ready.")
            return

    def _run_indexing(self, project_dir: Path):
        """Run normal indexing for the project."""
        console.info(f"Starting indexing for: {project_dir}")
        console.dim("   • Analyzing code structure and relationships")
        console.dim("   • Generating embeddings for semantic search")
        console.print()

        try:
            # Import and run indexing
            from cli.commands import handle_index_command

            # Mock args object for indexing
            class Args:
                project_path = str(project_dir)
                directory = str(project_dir)
                project_name = None
                log_level = self.log_level
                force = False

            args = Args()
            handle_index_command(args)

            console.success("Normal indexing completed successfully!")

        except Exception as e:
            console.error(f"Indexing failed: {e}")
            raise

    def _run_cross_indexing(self, project_dir: Path):
        """Run cross-indexing for the project."""

        # Check if cross-indexing is already completed
        try:
            from src.services.project_manager import ProjectManager
            from src.graph.graph_operations import GraphOperations

            project_manager = ProjectManager()
            graph_ops = GraphOperations()

            project_name = project_manager.determine_project_name(project_dir)

            if graph_ops.is_cross_indexing_done(project_name):
                console.success(f"Cross-indexing already completed for project '{project_name}'")
                console.dim("📊 Skipping analysis - project already fully analyzed")
                return

        except Exception as e:
            # If we can't check, proceed with the normal flow
            console.dim(f"⚠️ Could not verify cross-indexing status: {e}")

        warning_text = """
• ⏱️  Time: May take 5-30 minutes based on codebase size
• 🔥 Tokens: Will consume LLM tokens for deep analysis
• 🔄 Process: This is a one-time setup for this project
• 💻 Session: Do not close the terminal during this process

This analysis will create detailed inter-service connection mappings
for advanced code understanding and agent capabilities.
Closing the terminal or interrupting may lead to incomplete data and token wastage.
        """

        warning_panel = Panel(
            warning_text.strip(),
            title="⚠️  Cross-Indexing Analysis",
            border_style="yellow",
            title_align="left",
        )

        console.print(warning_panel)
        console.print()

        # Ask for user confirmation
        proceed = Confirm.ask(
            "[bold yellow]Do you want to proceed with cross-indexing analysis?[/bold yellow]",
            default=True,
        )

        if not proceed:
            console.warning("Cross-indexing declined by user.")
            console.dim("💡 Tip: You can run this later when you're ready to spend the time and tokens.")
            console.dim("📝 To continue later, simply run the same command again.")
            # Raise a custom exception to stop the workflow
            raise UserCancelledError("User declined cross-indexing analysis")

        # Use a simpler approach that doesn't conflict with the command's own output
        console.process("Starting cross-indexing analysis...")

        try:
            # Import and run cross-indexing
            from cli.commands import handle_cross_indexing_command

            # Mock args object for cross-indexing
            class Args:
                project_path = project_dir
                directory = str(project_dir)
                project_name = None
                log_level = "INFO"

            args = Args()
            handle_cross_indexing_command(args)

            console.success("Cross-indexing completed successfully!")

        except Exception as e:
            console.error(f"Cross-indexing failed: {e}")

    def _execute_agent(self, project_dir: Path, agent_name: Agent, agent_config):
        """Execute the actual agent."""
        console.highlight(f"Executing {agent_config.name}")

        try:
            from cli.commands import handle_agent_command

            # Execute the agent - post-processing is handled internally by the agent service
            agent_result = handle_agent_command(agent_name=agent_name, project_path=project_dir)

            if agent_result:
                console.success("Agent execution completed successfully!!!")
            else:
                console.warning("Agent execution completed with no result")

        except Exception as e:
            console.error(f"Agent execution failed: {e}")

    def run(self):
        """Main CLI execution flow."""
        # Show banner
        self.print_banner()

        # Check if LLM provider is configured
        if not self.check_llm_provider_configured():
            self.setup_llm_provider()
        else:
            console.success("LLM Provider already configured!")

        # Select agent
        selected_agent = self.select_agent()

        # Show prerequisites
        self.show_agent_prerequisites(selected_agent)

        # Confirm to proceed
        proceed = Confirm.ask("Ready to proceed with the agent workflow?", default=True)

        if not proceed:
            console.warning("Goodbye!")
            return

        # Get current directory
        current_dir = Path.cwd()

        # Run agent workflow
        try:
            self.run_agent_workflow(selected_agent, current_dir)
            console.success("🎉 SutraGraph workflow completed!")
            console.dim("Thank you for using SutraGraph!")
        except UserCancelledError:
            # This should already be handled in _run_roadmap_agent, but just in case
            pass


def main():
    """Main entry point for modern SutraGraph CLI."""
    try:
        cli = ModernSutraKit("INFO")
        cli.run()
    except KeyboardInterrupt:
        console.warning("Operation interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        console.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
