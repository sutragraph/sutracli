import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from prompt_toolkit import Application, prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from rich.prompt import Confirm, Prompt
from rich.table import Table

from src.config.settings import reload_config
from src.utils.console import console


class LLMProvider:
    def __init__(self, log_level: str = "INFO"):
        """Initialize the LLM Provider."""
        self.config_path = Path.home() / ".sutra" / "config" / "system.json"

    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if not self.config_path.exists():
            return {}

        with open(self.config_path, "r") as f:
            return json.load(f)

    def _get_llm_config(self) -> Dict:
        """Get LLM configuration section."""
        config_obj = self._load_config()

        return config_obj.get("llm", {})

    def validate_provider_config(self, provider: str, provider_config: Dict) -> bool:
        """Validate provider configuration against required fields.

        Args:
            provider: Provider key (e.g., 'anthropic', 'openai')
            provider_config: Dictionary containing provider configuration

        Returns:
            bool: True if all required fields are present and non-empty

        Raises:
            ValueError: If provider is not supported
        """
        from src.config.settings import get_provider_require_fields

        provider_required_fields = get_provider_require_fields()
        if provider not in provider_required_fields:
            raise ValueError(f"Invalid provider: {provider}")

        required_fields = provider_required_fields[provider]
        return all(provider_config.get(field) for field in required_fields)

    def _get_provider_config_from_file(self, provider: str) -> Optional[Dict]:
        """Get specific provider configuration from file.

        Returns:
            Provider config dict if exists and valid, None otherwise
        """
        llm_config = self._get_llm_config()
        provider_config = llm_config.get(provider, {})

        if not provider_config:
            return None

        try:
            if self.validate_provider_config(provider, provider_config):
                return provider_config
        except ValueError:
            return None

        return None

    def _display_provider_table(self, providers):
        """Display available providers in a table."""
        table = Table()
        table.add_column("Provider", style="green")
        table.add_column("Description", style="white")

        for provider in providers:
            table.add_row(provider["name"], provider["description"])

        console.print(table)
        console.print()

    def _display_current_config(self, provider_config: Dict) -> None:
        """Display current provider configuration."""
        console.info("Current configuration:")
        for key, value in provider_config.items():
            console.print(f"  {key}: {value}")

        console.print()

    def check_llm_provider_configured(self) -> bool:
        """Check if LLM provider is already configured.

        Returns:
            bool: True if a valid provider configuration exists
        """
        try:
            llm_config = self._get_llm_config()
            provider = llm_config.get("provider")

            if not provider:
                return False

            provider_config = self._get_provider_config_from_file(provider)
            return provider_config is not None

        except Exception:
            return False

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
                    lines.append(("class:selected", f"▶ {provider['name']}\n"))
                else:
                    lines.append(("", f"  {provider['name']}\n"))

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

    def _setup_provider_interactive(
        self, provider_key: str, existing_config: Optional[Dict] = None
    ) -> Dict:
        """Setup provider configuration interactively.

        Args:
            provider_key: Provider identifier
            existing_config: Existing configuration (if updating)

        Returns:
            Validated provider configuration
        """
        # Show existing config if available
        if existing_config:
            self._display_current_config(existing_config)
            if not Confirm.ask("Update the above configuration?"):
                return existing_config

        # Collect new configuration
        config_data = self._get_provider_config(provider_key)

        # Validate before returning
        if not self.validate_provider_config(provider_key, config_data):
            console.error("Invalid configuration provided")
            raise ValueError("Configuration validation failed")

        return config_data

    def setup_llm_provider(self):
        """Interactive LLM provider setup with arrow keys."""
        console.info("LLM Provider Setup")

        from src.config.settings import get_provider_info

        providers = get_provider_info()

        # Display provider options
        self._display_provider_table(providers)

        # Select provider
        selected_provider = self._arrow_key_select_provider(providers)
        if not selected_provider:
            console.error("No provider selected. Exiting.")
            sys.exit(1)

        provider_key = selected_provider["key"]
        console.success(f"Selected: {selected_provider['name']}")

        # Setup configuration (no existing config)
        config_data = self._setup_provider_interactive(provider_key)

        # Update and save
        updated_config = self._update_provider_config(provider_key, config_data)
        self._save_config(updated_config)

        console.success("Configuration saved successfully!")

    def switch_llm_provider(self):
        """Switch provider or update existing LLM provider configuration."""
        try:
            if not self.config_path.exists():
                raise ValueError("Sutrakit is not configured")

            console.info("LLM Provider Update")

            from src.config.settings import get_provider_info

            providers = get_provider_info()

            # Display provider options
            self._display_provider_table(providers)

            # Select provider
            selected_provider = self._arrow_key_select_provider(providers)
            if not selected_provider:
                console.error("No provider selected. Exiting.")
                sys.exit(1)

            provider_key = selected_provider["key"]
            console.success(f"Selected: {selected_provider['name']}")

            # Get existing config if available
            existing_config = self._get_provider_config_from_file(provider_key)

            # Setup configuration (with existing config if available)
            config_data = self._setup_provider_interactive(
                provider_key, existing_config
            )

            # Update and save
            updated_config = self._update_provider_config(provider_key, config_data)
            self._save_config(updated_config)

            console.success("Provider updated successfully!")

        except Exception as e:
            console.error(f"Error occurred: {str(e)}")
            raise
