"""
Configuration for external agent providers.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.config.settings import get_config, reload_config


@dataclass
class AgentProviderConfig:
    """Configuration for an external agent provider."""

    name: str
    command: str
    description: str
    enabled: bool = True
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class AgentProviderConfigManager:
    """Manages agent provider configurations using existing config system."""

    def __init__(self):
        self._providers: Dict[str, AgentProviderConfig] = {}
        self._initialize_default_providers()

    def _initialize_default_providers(self):
        """Initialize default provider configurations."""
        self._providers = {
            "rovodev": AgentProviderConfig(
                name="rovodev",
                command="acli rovodev",
                description="Rovodev CLI agent for code generation and analysis",
                enabled=True,
                config={"working_directory": None},
            ),
            "gemini": AgentProviderConfig(
                name="gemini",
                command="gemini",
                description="Google Gemini CLI for AI assistance",
                enabled=True,
                config={"working_directory": None},
            ),
        }

    def get_provider(self, name: str) -> Optional[AgentProviderConfig]:
        """Get a provider configuration by name."""
        return self._providers.get(name)

    def get_enabled_providers(self) -> Dict[str, AgentProviderConfig]:
        """Get all enabled providers."""
        return {
            name: provider
            for name, provider in self._providers.items()
            if provider.enabled
        }

    def set_selected_provider(self, provider_name: str) -> bool:
        """Set the selected provider and save to existing config system."""
        if provider_name not in self._providers:
            return False

        try:
            config = get_config()
            config_file = config.config_file

            # Load existing config
            with open(config_file, "r") as f:
                config_data = json.load(f)

            # Add agent provider selection
            if "agent_management" not in config_data:
                config_data["agent_management"] = {}

            config_data["agent_management"]["selected_provider"] = provider_name

            # Save updated config
            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            # Reload config to apply changes
            reload_config()

            return True

        except Exception as e:
            print(f"Error setting selected provider: {e}")
            return False

    def get_selected_provider(self) -> Optional[str]:
        """Get the currently selected provider from existing config system."""
        try:
            config = get_config()
            config_file = config.config_file

            with open(config_file, "r") as f:
                config_data = json.load(f)

            return config_data.get("agent_management", {}).get("selected_provider")
        except Exception:
            pass

        return None

    def list_providers(self) -> Dict[str, AgentProviderConfig]:
        """List all available providers."""
        return self._providers.copy()


# Global instance
_provider_config_manager = None


def get_provider_config_manager() -> AgentProviderConfigManager:
    """Get the global provider config manager instance."""
    global _provider_config_manager
    if _provider_config_manager is None:
        _provider_config_manager = AgentProviderConfigManager()
    return _provider_config_manager
