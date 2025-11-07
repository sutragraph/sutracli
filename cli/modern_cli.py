#!/usr/bin/env python3
"""
Modern CLI for SutraGraph - Interactive command-line interface with provider setup and agent management.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

# IMPORTANT: Setup logging FIRST before any imports that use loguru
# This prevents debug logs from appearing when log level is INFO
from baml_client.types import Agent
from src.utils.logging import setup_logging

# Set up basic INFO logging early to prevent debug logs during imports
# This will be reconfigured later in __init__ if a different level is requested
setup_logging("INFO")
from cli.llm_provider import LLMProvider
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from rich.align import Align
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from src.agent_management import AgentGraph
from src.agent_management.types.exception import AgentErrorType
from src.utils.console import console
from src.utils.version_checker import show_update_notification


class ModernSutraKit:
    """Modern interactive CLI for SutraGraph."""

    def __init__(self, log_level: str = "INFO"):
        """Initialize the modern CLI."""
        self.config_path = Path.home() / ".sutra" / "config" / "system.json"
        self.log_level = log_level

        # Reconfigure logging with the requested level (if different from initial INFO setup)
        if log_level != "INFO":
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
            border_style="bright_blue",
        )
        console.print(panel)

    def check_for_updates(self):
        """Check for SutraKit updates and show notification if available."""
        try:
            # Show update notification if available (non-blocking)
            show_update_notification()
        except Exception:
            # Silently fail if update check fails - don't interrupt the user experience
            pass

    def select_agent(self) -> Agent:
        """Interactive agent selection with arrow keys."""
        available_agents = AgentGraph.get_all_agents()

        console.info("Agent Selection")

        # Show available agents table
        if available_agents:
            table = Table()
            table.add_column("Agent", style="green")
            table.add_column("Description", style="white")

            for agent in available_agents:
                table.add_row(agent.name, AgentGraph.get_description(agent))

            console.print(table)

        console.print()

        if not available_agents:
            console.error("No agents available")
            sys.exit(1)

        # Use arrow key selection
        selected_agent = self._arrow_key_select_agents(available_agents)
        if selected_agent:
            return selected_agent
        else:
            console.error("No agent selected. Exiting.")
            sys.exit(1)

    def _arrow_key_select_agents(self, agents: List[Agent]) -> Optional[Agent]:
        """Custom arrow key selection for agents."""
        current_index = 0

        def get_formatted_text():
            lines = [
                (
                    "",
                    "Select agent (↑↓ to navigate, Enter to select, Esc to cancel):\n\n",
                )
            ]

            for i, agent in enumerate(agents):
                if i == current_index:
                    lines.append(("class:selected", f"▶ {agent.name}\n"))
                else:
                    lines.append(("", f"  {agent.name}\n"))

            return lines

        # Key bindings
        bindings = KeyBindings()

        @bindings.add("up")
        def move_up(event):
            nonlocal current_index
            current_index = (current_index - 1) % len(agents)

        @bindings.add("down")
        def move_down(event):
            nonlocal current_index
            current_index = (current_index + 1) % len(agents)

        @bindings.add("enter")
        def select_item(event):
            event.app.exit(result=agents[current_index])

        @bindings.add("escape")
        @bindings.add("c-c")
        def cancel(event):
            event.app.exit(result=None)

        # Create the application
        application = Application(
            layout=Layout(
                HSplit(
                    [
                        Window(
                            FormattedTextControl(get_formatted_text), wrap_lines=True
                        ),
                    ]
                )
            ),
            key_bindings=bindings,
            mouse_support=False,
            full_screen=False,
            style=Style(
                [
                    ("selected", "bg:#0066cc #ffffff bold"),
                    ("dim", "#666666"),
                ]
            ),
        )

        # Run the application
        return application.run()

    def show_agent_prerequisites(self, agent: Agent):
        """Show prerequisites for selected agent."""
        agent_config = AgentGraph.get_config(agent)

        if not agent_config:
            return

        console.success(f"Selected: {agent.name}")
        console.dim(agent_config.description)

        table = Table(show_header=False, box=None)
        table.add_column("Status", style="", width=3)
        table.add_column("Requirement", style="")

        # Add rows for each prerequisite
        for prereq in agent_config.prerequisites:
            status = "✓"  # or check actual status
            req_name = prereq.name.replace("_", " ").title()
            table.add_row(status, req_name)

        console.print(table)
        console.print()

    def run_agent_workflow(self, agent: Agent, current_dir: Path):
        """Run the workflow for selected agent."""
        try:
            self._execute_agent(agent, current_dir)

        except RuntimeError as e:
            # Check if it's a user cancellation error
            error_type = getattr(e, "error_type", None)
            if error_type == AgentErrorType.USER_CANCELLED:
                console.warning("Workflow stopped by user choice.")
                console.dim("You can restart the workflow anytime when ready.")
                return
            # Re-raise if it's a different runtime error
            raise

    def _execute_agent(self, agent: Agent, project_dir: Path):
        """Execute the actual agent."""
        console.print()
        console.highlight(f"Executing {agent.name}")

        try:
            # Get user query input
            while True:
                try:
                    user_input = input("\n👤 You: ").strip()
                    console.print("-" * 40)

                    if not user_input:
                        continue

                    # Got valid input, break out of input loop
                    break
                except KeyboardInterrupt:
                    console.print("\n\n👋 Goodbye! Session ended.")
                    return None
                except EOFError:
                    console.print("\n\n👋 Goodbye! Session ended.")
                    return None

            from src.agent_management.core.factory import AgentFactory

            try:
                agent_instance = AgentFactory.get_or_create(agent, project_dir)
            except ValueError as e:
                console.error(str(e))
                return None

            # All agents now use run_agent_loop
            agent_result = agent_instance.run_with_user_role(user_input)

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

        # Check for updates (non-blocking)
        self.check_for_updates()

        llm_provider = LLMProvider()
        # Check if LLM provider is configured
        if not llm_provider.check_llm_provider_configured():
            llm_provider.setup_llm_provider()
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
        except RuntimeError as e:
            # Check if it's a user cancellation - already handled in run_agent_workflow
            error_type = getattr(e, "error_type", None)
            if error_type == AgentErrorType.USER_CANCELLED:
                pass
            else:
                raise


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
