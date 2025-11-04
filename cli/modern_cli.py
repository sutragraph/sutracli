#!/usr/bin/env python3
"""
Modern CLI for SutraGraph - Interactive command-line interface with provider setup and agent management.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# IMPORTANT: Setup logging FIRST before any imports that use loguru
# This prevents debug logs from appearing when log level is INFO
from baml_client.types import Agent
from src.utils.logging import setup_logging

# Set up basic INFO logging early to prevent debug logs during imports
# This will be reconfigured later in __init__ if a different level is requested
setup_logging("INFO")
from dataclasses import dataclass
from typing import Callable

from prompt_toolkit import Application, prompt
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


@dataclass
class MenuOption:
    """Represents a menu option with display name and callback action."""

    name: str
    callback: Callable[[], None]


class ArrowKeySelector:
    """Handles arrow key selection for any type of options."""

    @staticmethod
    def select_option(options: list, title: str = "Select an option") -> Optional[Any]:
        """
        Generic arrow key selection menu that works with any list of options.

        Why: This creates a reusable selection interface that eliminates duplicate
        arrow key selection code for agents, providers, and options menus.

        Args:
            options: List of options (can be MenuOption objects, strings, or objects with .name)
            title: Title to display above the selection menu

        Returns:
            The selected option object or None if cancelled
        """
        current_index = 0

        def get_option_name(option):
            """Extract display name from different option types."""
            if isinstance(option, MenuOption):
                return option.name
            elif hasattr(option, "name"):
                return option.name
            elif isinstance(option, dict) and "name" in option:
                return option["name"]
            else:
                return str(option)

        def get_formatted_text():
            lines = [
                ("", f"{title} (↑↓ to navigate, Enter to select, Esc to cancel):\n\n")
            ]

            for i, option in enumerate(options):
                option_name = get_option_name(option)
                if i == current_index:
                    lines.append(("class:selected", f"▶ {option_name}\n"))
                else:
                    lines.append(("", f"  {option_name}\n"))

            return lines

        # Key bindings
        bindings = KeyBindings()

        @bindings.add("up")
        def move_up(event):
            nonlocal current_index
            current_index = (current_index - 1) % len(options)

        @bindings.add("down")
        def move_down(event):
            nonlocal current_index
            current_index = (current_index + 1) % len(options)

        @bindings.add("enter")
        def select_item(event):
            event.app.exit(result=options[current_index])

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


from src.agent_management import AgentGraph
from src.agent_management.core.registry import AgentRegistry
from src.agent_management.types.exception import AgentErrorType
from src.config.settings import reload_config
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

    def _get_user_input(self, prompt_msg: str = "👤 You: ") -> Optional[str]:
        """
        Reusable method to get user input with consistent error handling.

        Why: This eliminates the duplicate try/catch blocks for KeyboardInterrupt/EOFError
        that are repeated in _execute_agent, _continue_existing_session, and options menu.
        """
        while True:
            try:
                user_input = input(f"\n{prompt_msg}").strip()
                console.print("-" * 40)
                return user_input
            except KeyboardInterrupt:
                console.print("\n\n👋 Goodbye! Session ended.")
                return None
            except EOFError:
                console.print("\n\n👋 Goodbye! Session ended.")
                return None

    def _execute_agent_interaction(
        self, agent: Agent, project_dir: Path, user_input: str
    ) -> bool:
        """
        Execute a single agent interaction with consistent result handling.

        Why: This extracts the agent execution pattern that's duplicated between
        _execute_agent and _continue_existing_session methods.
        """
        agent_instance = AgentRegistry.get_or_create(agent, project_dir)

        agent_result = agent_instance.run_with_user_role(user_input)

        return True

    def _setup_and_execute_agent(self, agent: Agent, project_dir: Path) -> bool:
        """
        Set up agent prerequisites and get initial user input.

        Why: This extracts the common agent setup pattern that's needed for both
        initial execution and new session workflows.
        """
        try:
            agent_instance = AgentRegistry.get_or_create(agent, project_dir)

            if not agent_instance.run_prerequisites():
                console.error(
                    "Prerequisites failed. Cannot proceed with agent execution."
                )
                return False

            # Get initial user input
            while True:
                user_input = self._get_user_input()

                if user_input is None:
                    return False

                if not user_input:
                    continue

                return self._execute_agent_interaction(agent, project_dir, user_input)

        except ValueError as e:
            console.error(str(e))
            return False
        except Exception as e:
            console.error(f"Agent setup failed: {e}")
            return False

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

    def check_llm_provider_configured(self) -> bool:
        """Check if LLM provider is already configured."""
        try:
            if not self.config_path.exists():
                return False

            with open(self.config_path, "r") as f:
                config_data = json.load(f)

            llm_config = config_data.get("llm", {})
            provider = llm_config.get("provider")

            if not provider:
                return False

            # Check if provider-specific config exists
            provider_config = llm_config.get(provider, {})
            if not provider_config:
                return False

            # Basic validation for each provider
            if provider == "aws_bedrock":
                required_fields = [
                    "access_key_id",
                    "secret_access_key",
                    "model_id",
                    "region",
                ]
                return all(provider_config.get(field) for field in required_fields)
            elif provider == "anthropic":
                return bool(
                    provider_config.get("api_key") and provider_config.get("model_id")
                )
            elif provider == "openai":
                return bool(
                    provider_config.get("api_key") and provider_config.get("model_id")
                )
            elif provider == "google_ai":
                return bool(
                    provider_config.get("api_key")
                    and provider_config.get("model_id")
                    and provider_config.get("base_url")
                )
            elif provider == "vertex_ai":
                return bool(
                    provider_config.get("location") and provider_config.get("model_id")
                )
            elif provider == "azure_openai":
                required_fields = [
                    "api_key",
                    "base_url",
                    "api_version",
                ]
                return all(provider_config.get(field) for field in required_fields)
            elif provider == "azure_aifoundry":
                required_fields = [
                    "api_key",
                    "base_url",
                ]
                return all(provider_config.get(field) for field in required_fields)
            elif provider == "openrouter":
                required_fields = [
                    "api_key",
                    "model_id",
                ]
                return all(provider_config.get(field) for field in required_fields)

            return True

        except Exception:
            return False

    def _prompt_api_key(self, prompt_text, is_password=True, error_message=None):
        """Utility to prompt for API key or secret with validation."""
        while True:
            key = prompt(prompt_text, is_password=is_password)
            if key.strip():
                return key
            console.error(
                error_message or f"{prompt_text} is required and cannot be empty."
            )

    def _prompt_input(self, prompt_text, default=None, error_message=None):
        """Generic utility to prompt for any required input with validation and optional default."""
        while True:
            if default is not None:
                value = Prompt.ask(prompt_text, default=default)
            else:
                value = Prompt.ask(prompt_text)
            if value.strip():
                return value
            console.error(
                error_message or f"{prompt_text} is required and cannot be empty."
            )

    def _prompt_max_tokens(self, info_message=None, dim_message=None, default=None):
        """Utility to prompt for max tokens with validation and optional info/dim messages."""
        if info_message:
            console.info(info_message)
        if dim_message:
            console.dim(dim_message)
        while True:
            if default is not None:
                max_tokens = Prompt.ask("Max tokens", default=str(default))
            else:
                max_tokens = Prompt.ask("Max tokens")
            if max_tokens.strip():
                try:
                    int(max_tokens.strip())
                    return max_tokens
                except ValueError:
                    console.error("Max tokens must be a valid number.")
            else:
                console.error("Max tokens is required and cannot be empty.")

    def setup_llm_provider(self):
        """Interactive LLM provider setup with arrow keys."""
        console.info("LLM Provider Setup")

        # Import providers from centralized config
        from src.config.settings import get_provider_info

        providers = get_provider_info()

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

        # Update the provider configuration in existing config
        updated_config = self._update_provider_config(provider_key, config_data)

        # Save configuration
        self._save_config(updated_config)

        console.success("Configuration saved successfully!")

    def _get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for specific provider."""
        if provider == "aws_bedrock":
            return self._get_aws_config()
        elif provider == "anthropic":
            return self._get_anthropic_config()
        elif provider == "google_ai":
            return self._get_gemini_config()
        elif provider == "vertex_ai":
            return self._get_vertex_ai_config()
        elif provider == "azure_openai":
            return self._get_azure_config()
        elif provider == "openai":
            return self._get_openai_config()
        elif provider == "azure_aifoundry":
            return self._get_azure_aifoundry_config()
        elif provider == "openrouter":
            return self._get_openrouter_config()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _get_aws_config(self) -> Dict[str, Any]:
        """Get AWS Bedrock configuration."""
        console.info("AWS Bedrock Configuration")
        access_key = self._prompt_api_key(
            "AWS Access Key ID",
            is_password=False,
            error_message="AWS Access Key ID is required and cannot be empty.",
        )
        secret_key = self._prompt_api_key(
            "AWS Secret Access Key: ",
            is_password=True,
            error_message="AWS Secret Access Key is required and cannot be empty.",
        )
        region = Prompt.ask("AWS Region", default="us-east-2")
        model_id = self._prompt_input(
            prompt_text="Model ID", default="us.anthropic.claude-sonnet-4-20250514-v1:0"
        )
        console.print()
        max_tokens = self._prompt_max_tokens(
            info_message="Maximum output tokens per response for your model",
            dim_message="Common values: Claude Sonnet 4: 64000, Claude Haiku: 64000",
        )
        return {
            "access_key_id": access_key,
            "secret_access_key": secret_key,
            "region": region,
            "model_id": model_id,
            "max_tokens": max_tokens,
        }

    def _get_anthropic_config(self) -> Dict[str, Any]:
        """Get Anthropic configuration."""
        console.info("Anthropic Configuration")
        api_key = self._prompt_api_key(
            "Anthropic API Key: ",
            is_password=True,
            error_message="Anthropic API Key is required and cannot be empty.",
        )
        model_id = self._prompt_input(
            prompt_text="Model ID", default="claude-4-sonnet-20250514"
        )
        console.print()
        max_tokens = self._prompt_max_tokens(
            info_message="Maximum output tokens per response for your model",
            dim_message="Common values: Claude Sonnet 4: 64000, Claude Haiku: 64000",
        )
        return {"api_key": api_key, "model_id": model_id, "max_tokens": max_tokens}

    def _get_gemini_config(self) -> Dict[str, Any]:
        """Get Google Gemini configuration."""
        console.info("Google Gemini Configuration")
        api_key = self._prompt_api_key(
            "Gemini API Key: ",
            is_password=True,
            error_message="Gemini API Key is required and cannot be empty.",
        )
        model_id = self._prompt_input(prompt_text="Model ID", default="gemini-2.5-pro")
        base_url = self._prompt_input(
            prompt_text="Base URL",
            default="https://generativelanguage.googleapis.com/v1beta",
        )
        console.print()
        max_tokens = self._prompt_max_tokens(
            info_message="Maximum output tokens per response for your model",
            dim_message="Common values: Gemini 2.5 Pro: 64000, Gemini 1.5 Flash: 64000",
        )
        return {
            "api_key": api_key,
            "model_id": model_id,
            "base_url": base_url,
            "max_tokens": max_tokens,
        }

    def _get_vertex_ai_config(self) -> Dict[str, Any]:
        """Get Google Cloud Vertex AI configuration with gcloud authentication."""
        console.info("Google Cloud Vertex AI Configuration")
        console.print()
        console.info("Vertex AI uses Google Cloud authentication via gcloud CLI.")
        console.print("Please ensure you have:")
        console.print(
            "  1. Google Cloud SDK installed (https://cloud.google.com/sdk/docs/install)"
        )
        console.print(
            "  2. Run: gcloud init (to set up your default project and authentication)"
        )
        console.print("  3. Vertex AI API enabled in your project")
        console.print("  4. Proper permissions for Vertex AI")
        console.print()

        # Prompt for authentication
        if Confirm.ask("Do you want to authenticate with Google Cloud now?"):
            self._setup_gcp_auth()
        else:
            console.warning(
                "You can authenticate later using: gcloud auth application-default login --project YOUR_PROJECT_ID"
            )

        # Get basic configuration
        location = Prompt.ask("Location (region)", default="global")
        model_id = self._prompt_input(prompt_text="Model ID", default="gemini-2.5-pro")
        console.print()
        max_tokens = self._prompt_max_tokens(
            info_message="Maximum output tokens per response for your model",
            dim_message="Common values: Gemini 2.5 Pro: 64000, Gemini 2.5 Flash: 64000",
        )
        return {"location": location, "model_id": model_id, "max_tokens": max_tokens}

    def _setup_gcp_auth(self):
        """Guide user through GCP authentication setup with retry option."""
        import subprocess

        console.info("Setting up Google Cloud authentication...")

        # Check if gcloud is installed
        try:
            result = subprocess.run(
                ["gcloud", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                console.error("Google Cloud SDK (gcloud) is not installed.")
                console.info(
                    "Please install it from: https://cloud.google.com/sdk/docs/install"
                )
                console.info("After installation, run: gcloud init")
                return
        except FileNotFoundError:
            console.error("Google Cloud SDK (gcloud) is not installed or not in PATH.")
            console.info(
                "Please install it from: https://cloud.google.com/sdk/docs/install"
            )
            console.info("After installation, run: gcloud init")
            return

        # Retry loop for authentication
        while True:
            # Get project ID
            while True:
                project_id = Prompt.ask("Enter your Google Cloud Project ID")
                if project_id.strip():
                    break
                console.error(
                    "Google Cloud Project ID is required and cannot be empty."
                )

            # Run authentication command
            console.info(
                f"Running: gcloud auth application-default login --project {project_id}"
            )
            console.info("This will open your browser for authentication...")

            try:
                result = subprocess.run(
                    [
                        "gcloud",
                        "auth",
                        "application-default",
                        "login",
                        "--project",
                        project_id,
                    ],
                    check=True,
                )

                if result.returncode == 0:
                    console.success("Google Cloud authentication successful!")
                    console.info("Vertex AI is now ready to use.")
                    return  # Success, exit the retry loop

            except subprocess.CalledProcessError as e:
                console.error(f"Authentication failed: {e}")
                console.info("Steps:")
                console.info("1. Run: gcloud init (if not done already)")
                console.info(
                    f"2. Run: gcloud auth application-default login --project {project_id}"
                )
            except Exception as e:
                console.error(f"Unexpected error: {e}")
                console.info("Steps:")
                console.info("1. Run: gcloud init (if not done already)")
                console.info(
                    f"2. Run: gcloud auth application-default login --project {project_id}"
                )

            # Ask if user wants to retry
            console.print()
            if not Confirm.ask(
                "Would you like to try again with a different project ID or retry authentication?",
                default=True,
            ):
                console.warning(
                    "Authentication setup cancelled. You can set up authentication manually later."
                )
                break

    def _get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration."""
        console.info("OpenAI Configuration")
        api_key = self._prompt_api_key(
            "OpenAI API Key: ",
            is_password=True,
            error_message="OpenAI API Key is required and cannot be empty.",
        )
        model_id = self._prompt_input(prompt_text="Model ID", default="gpt-4.1")
        console.print()
        max_tokens = self._prompt_max_tokens(
            info_message="Maximum output tokens per response for your model",
            dim_message="Common values: GPT-4.1: 32768, GPT-5: 128000, GPT-4o: 64000",
        )
        return {"api_key": api_key, "model_id": model_id, "max_tokens": max_tokens}

    def _get_azure_config(self) -> Dict[str, Any]:
        """Get Azure OpenAI configuration."""
        console.info("Azure OpenAI Configuration")
        api_key = self._prompt_api_key(
            "Azure OpenAI API Key: ",
            is_password=True,
            error_message="Azure OpenAI API Key is required and cannot be empty.",
        )
        console.print()
        console.info(
            "Base URL Example: https://your-resource-name.openai.azure.com/openai/deployments/your-deployment-id"
        )
        console.dim(
            "Replace 'your-resource-name' with your Azure resource name and 'your-deployment-id' with your deployment ID"
        )
        console.print()
        base_url = self._prompt_input(prompt_text="Base URL")
        api_version = self._prompt_input(
            prompt_text="API Version", default="2025-01-01-preview"
        )
        console.print()
        max_tokens = self._prompt_max_tokens(
            info_message="Maximum output tokens per response for your model",
            dim_message="Common values: GPT-4.1: 32768, GPT-5: 128000, GPT-4o: 64000",
        )
        return {
            "api_key": api_key,
            "base_url": base_url,
            "api_version": api_version,
            "max_tokens": max_tokens,
        }

    def _get_azure_aifoundry_config(self) -> Dict[str, Any]:
        """Get Azure AI Foundry configuration."""
        console.info("Azure AI Foundry Configuration")
        api_key = self._prompt_api_key(
            "Azure AI Foundry API Key: ",
            is_password=True,
            error_message="Azure AI Foundry API Key is required and cannot be empty.",
        )
        console.print()
        console.info(
            "Base URL Example: https://RESOURCE_NAME.REGION.models.ai.azure.com"
        )
        console.dim(
            "Replace 'RESOURCE_NAME' with your Azure resource name and 'REGION' with your region"
        )
        console.print()
        base_url = self._prompt_input(prompt_text="Base URL")
        console.print()
        max_tokens = self._prompt_max_tokens(
            info_message="Maximum output tokens per response for your model",
            dim_message="Common values: GPT-4.1: 32768, GPT-5: 128000, Claude Sonnet 4: 64000 check model specs",
        )
        return {
            "api_key": api_key,
            "base_url": base_url,
            "max_tokens": max_tokens,
        }

    def _get_openrouter_config(self) -> Dict[str, Any]:
        """Get OpenRouter configuration."""
        console.info("OpenRouter Configuration")
        api_key = self._prompt_api_key(
            "OpenRouter API Key: ",
            is_password=True,
            error_message="OpenRouter API Key is required and cannot be empty.",
        )
        model_id = self._prompt_input(
            prompt_text="Model ID", default="openai/gpt-3.5-turbo"
        )
        console.print()
        console.info("Optional headers (press Enter to skip):")
        http_referer = Prompt.ask("HTTP-Referer (your site URL)", default="")
        x_title = Prompt.ask("X-Title (your app title)", default="")
        console.print()
        max_tokens = self._prompt_max_tokens(
            info_message="Maximum output tokens per response for your model",
            dim_message="Common values: GPT-4.1: 32768, GPT-5: 128000, Claude Sonnet 4: 64000, Gemini 2.5 Pro: 64000 check model specs",
        )
        config = {
            "api_key": api_key,
            "model_id": model_id,
            "max_tokens": max_tokens,
        }
        # Only add optional headers if they have values
        if http_referer:
            config["http_referer"] = http_referer
        if x_title:
            config["x_title"] = x_title
        return config

    def _update_provider_config(self, provider: str, provider_config: Dict[str, Any]):
        """Update only the provider configuration in existing config file."""
        # Load existing config or create minimal structure if it doesn't exist
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    existing_config = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_config = {}
        else:
            existing_config = {}

        # Ensure llm section exists
        if "llm" not in existing_config:
            existing_config["llm"] = {}

        # Update provider and max_tokens
        existing_config["llm"]["provider"] = provider

        # Initialize all provider sections if they don't exist
        provider_keys = [
            "aws_bedrock",
            "anthropic",
            "google_ai",
            "vertex_ai",
            "azure_openai",
            "openai",
            "azure_aifoundry",
            "openrouter",
            "superllm",
        ]
        for key in provider_keys:
            if key not in existing_config["llm"]:
                existing_config["llm"][key] = {}

        # Update only the fields provided by the user, preserving existing fields
        if provider in existing_config["llm"]:
            # Merge new config with existing provider config
            for field_key, field_value in provider_config.items():
                existing_config["llm"][provider][field_key] = field_value
        else:
            # If provider section doesn't exist, create it with the new config
            existing_config["llm"][provider] = provider_config

        return existing_config

    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

        # Reload the configuration to update the in-memory instance
        reload_config()
        # Check Vertex AI authentication if using vertex_ai provider
        from src.config.settings import get_config

        config_obj = get_config()
        if config_obj.llm.provider.lower() == "vertex_ai":
            from cli.setup import _check_vertex_ai_auth

            _check_vertex_ai_auth()

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

        # Use arrow key selection with the new ArrowKeySelector
        selected_agent = ArrowKeySelector.select_option(
            available_agents, "Select agent"
        )

        if selected_agent:
            return selected_agent
        else:
            console.error("No agent selected. Exiting.")
            sys.exit(1)

    def _arrow_key_select_provider(self, providers):
        """Arrow key selection for LLM providers using ArrowKeySelector."""
        return ArrowKeySelector.select_option(providers, "Select LLM provider")

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

        if self._setup_and_execute_agent(agent, project_dir):
            console.success("Agent execution completed successfully!!!")
        else:
            console.warning("Agent execution completed with no result")

        # Show options menu after agent completion
        self._show_post_completion_options(agent, project_dir)

    def _show_post_completion_options(self, agent: Agent, project_dir: Path):
        """Show options menu after agent completion."""
        console.print("\n" + "=" * 50)

        # Define options with callbacks
        options = [
            MenuOption(
                "Continue with existing session",
                lambda: self._continue_existing_session(agent, project_dir),
            ),
            MenuOption(
                "Start new session", lambda: self._start_new_session(project_dir)
            ),
            MenuOption(
                "Quit",
                lambda: console.success("Goodbye! Thank you for using SutraGraph!"),
            ),
        ]

        selected_option = ArrowKeySelector.select_option(
            options, "What would you like to do next?"
        )

        if selected_option is None:  # User pressed Esc/Ctrl+C
            return

        # Execute the callback for the selected option
        selected_option.callback()

        # If quit was selected, we need to return from the method
        if selected_option.name == "Quit":
            return

    def _continue_existing_session(self, agent: Agent, project_dir: Path):
        """Continue with the existing session by prompting for user input."""
        console.info(f"Continuing with {agent.name} session...")
        console.print("You can continue interacting with the agent.")
        console.print()

        while True:
            user_input = self._get_user_input()

            if user_input is None:
                return

            if not user_input:
                continue

            # Execute agent with user input
            self._execute_agent_interaction(agent, project_dir, user_input)

            # After each interaction, show options menu again
            console.info("Agent interaction completed!")
            self._show_post_completion_options(agent, project_dir)
            return

    def _start_new_session(self, project_dir: Path):
        """Start a new session by clearing registry and selecting new agent."""
        console.info("Starting new session...")

        # Clear all agent instances from registry
        AgentRegistry.clear_all_instances()
        console.success("All previous sessions cleared.")

        # Select new agent
        new_agent = self.select_agent()

        # Show prerequisites for new agent
        self.show_agent_prerequisites(new_agent)

        # Confirm to proceed
        proceed = Confirm.ask(
            "Ready to proceed with the new agent workflow?", default=True
        )

        if not proceed:
            console.info("Returning to options menu...")
            self._show_post_completion_options(new_agent, project_dir)
            return

        # Execute new agent workflow
        console.print()
        console.highlight(f"Executing {new_agent.name}")

        if self._setup_and_execute_agent(new_agent, project_dir):
            console.success("New agent execution completed successfully!!!")
        else:
            console.warning("New agent execution completed with no result")

        # Show options menu after completion
        self._show_post_completion_options(new_agent, project_dir)

    def run(self):
        """Main CLI execution flow."""
        # Show banner
        self.print_banner()

        # Check for updates (non-blocking)
        self.check_for_updates()

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
