#!/usr/bin/env python3
"""
Modern CLI for SutraGraph - Interactive command-line interface with provider setup and agent management.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Prompt toolkit imports for arrow key navigation
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

from src.agent_management.prerequisites.agent_config import get_agent_registry
from src.agents_new import Agent
from src.config.settings import reload_config
from src.utils.console import console
from src.utils.logging import setup_logging
from src.utils.version_checker import show_update_notification


class UserCancelledError(Exception):
    """Exception raised when user cancels an operation."""

    pass


class ModernSutraKit:
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
            lines = [
                (
                    "",
                    "Select LLM provider (↑↓ to navigate, Enter to select, Esc to cancel):\n\n",
                )
            ]

            for i, provider in enumerate(providers):
                if i == current_index:
                    lines.append(("class:selected", f'▶ {provider["name"]}\n'))
                else:
                    lines.append(("", f'  {provider["name"]}\n'))

            return lines

        # Key bindings
        bindings = KeyBindings()

        @bindings.add("up")
        def move_up(event):
            nonlocal current_index
            current_index = (current_index - 1) % len(providers)

        @bindings.add("down")
        def move_down(event):
            nonlocal current_index
            current_index = (current_index + 1) % len(providers)

        @bindings.add("enter")
        def select_item(event):
            event.app.exit(result=providers[current_index])

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

    def _arrow_key_select_agents(self, agents):
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
                    lines.append(("class:selected", f"▶ {agent.name}"))
                else:
                    lines.append(("", f"  {agent.name}"))

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
            from src.graph.graph_operations import GraphOperations
            from src.services.project_manager import ProjectManager

            project_manager = ProjectManager()
            graph_ops = GraphOperations()

            project_name = project_manager.determine_project_name(project_dir)

            if graph_ops.is_cross_indexing_done(project_name):
                console.success(
                    f"Cross-indexing already completed for project '{project_name}'"
                )
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
            console.dim(
                "💡 Tip: You can run this later when you're ready to spend the time and tokens."
            )
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
            agent_result = handle_agent_command(
                agent_name=agent_name, project_path=project_dir
            )

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
