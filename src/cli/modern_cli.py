#!/usr/bin/env python3
"""
Modern CLI for SutraGraph - Interactive command-line interface with provider setup and agent management.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
from rich.console import Console
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

from src.agent_management.prerequisites.agent_config import (
    get_agent_registry,
)
from cli.utils import setup_logging
from config.settings import reload_config


class UserCancelledError(Exception):
    """Exception raised when user cancels an operation."""

    pass


class ModernSutraKit:
    """Modern interactive CLI for SutraGraph."""

    def __init__(self, log_level: str = "INFO"):
        """Initialize the modern CLI."""
        self.console = Console()
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
        self.console.print(panel)

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
        self.console.print("[bold yellow]⚙️  LLM Provider Setup[/bold yellow]")

        providers = [
            {"name": "Anthropic (Claude)", "key": "anthropic", "description": "Claude models (claude-3.5-sonnet, etc.)"},
            {"name": "AWS Bedrock", "key": "aws", "description": "AWS managed AI services"},
            {"name": "Google Gemini", "key": "gcp", "description": "Google's Gemini models"},
            {"name": "OpenAI (ChatGPT)", "key": "openai", "description": "GPT models via OpenAI API"}
        ]

        table = Table()
        table.add_column("Provider", style="green")
        table.add_column("Description", style="white")

        for provider in providers:
            table.add_row(provider["name"], provider["description"])

        self.console.print(table)
        self.console.print()

        selected_provider = self._arrow_key_select_provider(providers)
        if not selected_provider:
            self.console.print("[red]❌ No provider selected. Exiting.[/red]")
            sys.exit(1)

        provider_key = selected_provider["key"]
        self.console.print(f"[green]✅ Selected: {selected_provider['name']}[/green]\n")

        # Collect provider-specific configuration
        config_data = self._get_provider_config(provider_key)

        # Create the full configuration
        full_config = self._create_full_config(provider_key, config_data)

        # Save configuration
        self._save_config(full_config)

        self.console.print("[green]✅ Configuration saved successfully![/green]\n")

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
        self.console.print("[bold blue]🔧 AWS Bedrock Configuration[/bold blue]")
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
        self.console.print("[bold blue]🔧 Anthropic Configuration[/bold blue]")
        api_key = prompt("Anthropic API Key: ", is_password=True)
        model_id = Prompt.ask("Model ID", default="claude-3-5-sonnet-20241022")

        return {
            "api_key": api_key,
            "model_id": model_id
        }

    def _get_gcp_config(self) -> Dict[str, Any]:
        """Get Google Cloud configuration."""
        self.console.print("[bold blue]🔧 Google Cloud Configuration[/bold blue]")
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
        self.console.print("[bold blue]🔧 OpenAI Configuration[/bold blue]")
        api_key = prompt("OpenAI API Key: ", is_password=True)
        model_id = Prompt.ask("Model ID", default="gpt-4o")

        return {
            "api_key": api_key,
            "model_id": model_id
        }

    def _create_full_config(self, provider: str, provider_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create full configuration with default values."""
        return {
            "database": {
                "knowledge_graph_db": "~/.sutra/data/knowledge_graph.db",
                "embeddings_db": "~/.sutra/data/knowledge_graph_embeddings.db",
                "connection_timeout": 60,
                "max_retry_attempts": 5,
                "batch_size": 1000,
                "enable_wal_mode": True
            },
            "storage": {
                "data_dir": "~/.sutra/data",
                "sessions_dir": "~/.sutra/data/sessions",
                "file_changes_dir": "~/.sutra/data/file_changes",
                "file_edits_dir": "~/.sutra/data/edits",
                "parser_results_dir": "~/.sutra/parser_results",
                "models_dir": "~/.sutra/models"
            },
            "embedding": {
                "model_name": "all-MiniLM-L12-v2",
                "model_path": "~/.sutra/models/all-MiniLM-L12-v2",
                "max_tokens": 240,
                "overlap_tokens": 30,
                "similarity_threshold": 0.2,
                "enable_optimization": False
            },
            "parser": {
                "config_file": "~/.sutra/config/parsers.json",
                "build_directory": "~/.sutra/build"
            },
            "web_search": {
                "api_key": "YOUR_WEB_SEARCH_API_KEY",
                "requests_per_minute": 60,
                "timeout": 30
            },
            "web_scrap": {
                "timeout": 30,
                "max_retries": 3,
                "delay_between_retries": 1.0,
                "include_comments": True,
                "include_tables": True,
                "include_images": True,
                "include_links": True,
                "trafilatura_config": {},
                "markdown_options": {
                    "heading_style": "ATX",
                    "bullets": "-",
                    "wrap": True
                }
            },
            "logging": {
                "level": "INFO",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
                "log_file": "~/.sutra/logs/sutraknowledge.log"
            },
            "llm": {
                "provider": provider,
                "llama_model_id": "meta/llama-4-maverick-17b-128e-instruct-maas",
                "gemini_model": "gemini-2.5-flash",
                "claude_model": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                "aws": provider_config if provider == "aws" else {},
                "anthropic": provider_config if provider == "anthropic" else {},
                "gcp": provider_config if provider == "gcp" else {},
                "openai": provider_config if provider == "openai" else {},
                "superllm": {}
            }
        }

    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Reload the configuration to update the in-memory instance
        reload_config()

    def select_agent(self) -> str:
        """Interactive agent selection with arrow keys."""
        available_agents = self.agent_registry.get_available_agents()

        self.console.print("[bold yellow]🤖 Agent Selection[/bold yellow]")

        # Show available agents table
        if available_agents:
            table = Table()
            table.add_column("Agent", style="green")
            table.add_column("Description", style="white")

            for agent in available_agents:
                table.add_row(agent.name, agent.description)

            self.console.print(table)

        self.console.print()

        if not available_agents:
            self.console.print("[red]❌ No agents available[/red]")
            return "roadmap"

        # Use arrow key selection
        selected_agent = self._arrow_key_select_agents(available_agents)
        if selected_agent:
            return selected_agent.key
        else:
            self.console.print("[red]❌ No agent selected. Exiting.[/red]")
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

    def show_agent_prerequisites(self, agent_key: str):
        """Show prerequisites for selected agent."""
        agent_config = self.agent_registry.get_agent(agent_key)
        if not agent_config:
            return

        self.console.print(f"[bold green]✅ Selected: {agent_config.name}[/bold green]")
        self.console.print(f"[dim]{agent_config.description}[/dim]")

        table = Table(show_header=False, box=None)
        table.add_column("Status", style="", width=3)
        table.add_column("Requirement", style="")
        table.add_column("Description", style="dim")

        self.console.print(table)
        self.console.print()

    def run_agent_workflow(self, agent_key: str, current_dir: Path):
        """Run the workflow for selected agent."""
        agent_config = self.agent_registry.get_agent(agent_key)
        if not agent_config:
            self.console.print(f"[red]❌ Agent '{agent_key}' not found.[/red]")
            return

        # Check if agent is available (implemented)
        available_agents = self.agent_registry.get_available_agents()
        if agent_config not in available_agents:
            self.console.print(f"[yellow]🚧 Agent '{agent_config.name}' is not yet implemented.[/yellow]")
            return

        try:
            # Check if indexing is required
            if agent_config.requires_indexing:
                self._run_indexing(current_dir)

            # Check if cross-indexing is required
            if agent_config.requires_cross_indexing:
                self._run_cross_indexing(current_dir)

            # Run the actual agent
            if agent_key == "roadmap":
                self._run_roadmap_agent(current_dir, agent_config)
            else:
                self.console.print(
                    f"[red]❌ Agent '{agent_key}' not implemented yet.[/red]"
                )

        except UserCancelledError:
            self.console.print("[yellow]👋 Workflow stopped by user choice.[/yellow]")
            self.console.print(
                "[dim]You can restart the workflow anytime when ready.[/dim]"
            )
            return

    def _run_roadmap_agent(self, current_dir: Path, agent_config):
        """Run the roadmap agent workflow."""
        self.console.print(
            "[bold blue]🚀 Starting Roadmap Agent Workflow[/bold blue]\n"
        )

        # Run the actual agent (prerequisites are now handled in run_agent_workflow)
        self._execute_agent(current_dir, agent_config)

    def _run_indexing(self, project_dir: Path):
        """Run normal indexing for the project."""
        self.console.print(f"[blue]📁 Starting indexing for:[/blue] {project_dir}")
        self.console.print("[dim]   • Analyzing code structure and relationships[/dim]")
        self.console.print("[dim]   • Generating embeddings for semantic search[/dim]")
        self.console.print()

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

            self.console.print("[green]✅ Normal indexing completed successfully![/green]\n")

        except Exception as e:
            self.console.print(f"[red]❌ Indexing failed: {e}[/red]\n")
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
                self.console.print(
                    f"[green]✅ Cross-indexing already completed for project '{project_name}'[/green]"
                )
                self.console.print(
                    "[dim]📊 Skipping analysis - project already fully analyzed[/dim]\n"
                )
                return

        except Exception as e:
            # If we can't check, proceed with the normal flow
            self.console.print(
                f"[dim]⚠️ Could not verify cross-indexing status: {e}[/dim]"
            )

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

        self.console.print(warning_panel)
        self.console.print()

        # Ask for user confirmation
        proceed = Confirm.ask(
            "[bold yellow]Do you want to proceed with cross-indexing analysis?[/bold yellow]",
            default=True,
        )

        if not proceed:
            self.console.print("[yellow]🛑 Cross-indexing declined by user.[/yellow]")
            self.console.print(
                "[dim]💡 Tip: You can run this later when you're ready to spend the time and tokens.[/dim]"
            )
            self.console.print(
                "[dim]📝 To continue later, simply run the same command again.[/dim]\n"
            )
            # Raise a custom exception to stop the workflow
            raise UserCancelledError("User declined cross-indexing analysis")

        # Use a simpler approach that doesn't conflict with the command's own output
        self.console.print("[cyan]🔄 Starting cross-indexing analysis...[/cyan]")

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

            self.console.print(
                "[green]✅ Cross-indexing completed successfully![/green]\n"
            )

        except Exception as e:
            self.console.print(f"[red]❌ Cross-indexing failed: {e}[/red]\n")

    def _execute_agent(self, project_dir: Path, agent_config):
        """Execute the actual agent."""
        self.console.print(f"[bold green]🎯 Executing {agent_config.name}[/bold green]")

        try:
            from cli.commands import handle_agent_command
            from src.agent_management.post_requisites.handlers import get_agent_handler

            # Get query from user
            user_query = Prompt.ask(
                "[bold cyan]💭 Enter your query for the Roadmap Agent[/bold cyan]",
                default="Analyze this codebase and provide development insights",
            )

            # Mock args object for agent execution
            class Args:

                def __init__(self):
                    self.agent_type = agent_config.key
                    self.project_path = project_dir
                    self.directory = str(project_dir)
                    self.project_name = None
                    self.problem_query = user_query
                    self.project_id = None
                    self.log_level = "INFO"

            args = Args()

            # Execute the agent and capture result
            agent_result = handle_agent_command(args)

            self.console.print(f"[green]✅ {agent_config.name} completed successfully![/green]")

            # Handle post-requisites if agent returned results
            if agent_result:
                self.console.print(
                    f"[blue]🔄 Processing {agent_config.name} results...[/blue]"
                )

                # Get appropriate handler for this agent and process results directly
                handler = get_agent_handler(agent_config.key)

                # Process the agent result directly - no wrapper needed
                post_result = handler.process_agent_result_direct(agent_result)

                if post_result.get("success"):
                    self.console.print(
                        "[green]✅ Post-processing completed successfully![/green]"
                    )

                    # Show details if available
                    processed_actions = post_result.get("processed_actions", [])
                    if processed_actions:
                        self.console.print(
                            f"[dim]Processed {len(processed_actions)} post-requisite actions[/dim]"
                        )
                        for action in processed_actions:
                            if action.get("success"):
                                self.console.print(
                                    f"[green]  ✓ {action['action']}: {action.get('message', 'Success')}[/green]"
                                )
                            else:
                                self.console.print(
                                    f"[red]  ✗ {action['action']}: {action.get('error', 'Failed')}[/red]"
                                )
                else:
                    self.console.print(
                        f"[yellow]⚠️ Post-processing completed with issues: {post_result.get('message', 'Unknown error')}[/yellow]"
                    )

        except Exception as e:
            self.console.print(f"[red]❌ Agent execution failed: {e}[/red]")

    def run(self):
        """Main CLI execution flow."""
        # Show banner
        self.print_banner()

        # Check if LLM provider is configured
        if not self.check_llm_provider_configured():
            self.setup_llm_provider()
        else:
            self.console.print("[green]✅ LLM Provider already configured![/green]\n")

        # Select agent
        selected_agent = self.select_agent()

        # Show prerequisites
        self.show_agent_prerequisites(selected_agent)

        # Confirm to proceed
        proceed = Confirm.ask("Ready to proceed with the agent workflow?", default=True)

        if not proceed:
            self.console.print("[yellow]👋 Goodbye![/yellow]")
            return

        # Get current directory
        current_dir = Path.cwd()

        # Run agent workflow
        try:
            self.run_agent_workflow(selected_agent, current_dir)
            self.console.print(
                "\n[bold green]🎉 SutraGraph workflow completed![/bold green]"
            )
            self.console.print("[dim]Thank you for using SutraGraph![/dim]")
        except UserCancelledError:
            # This should already be handled in _run_roadmap_agent, but just in case
            pass


def main():
    """Main entry point for modern SutraGraph CLI."""
    try:
        cli = ModernSutraKit("INFO")
        cli.run()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]👋 Operation interrupted. Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"\n[red]❌ An error occurred: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
