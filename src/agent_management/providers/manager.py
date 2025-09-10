"""
Manager for external agent providers.
"""

import concurrent.futures
import threading
from typing import Any, Dict, List, Optional

from tools.tool_terminal_commands.action import TerminalSessionManager

from .config import AgentProviderConfig, get_provider_config_manager
from .gemini import GeminiProvider
from .rovodev import RovodevProvider


class AgentProviderManager:
    """Manages external agent providers and their execution."""

    def __init__(self):
        self.config_manager = get_provider_config_manager()
        self._providers = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all available providers."""
        provider_configs = self.config_manager.list_providers()

        for name, config in provider_configs.items():
            if name == "rovodev":
                self._providers[name] = RovodevProvider(config)
            elif name == "gemini":
                self._providers[name] = GeminiProvider(config)

    def get_provider(self, name: str) -> Optional[object]:
        """Get a provider instance by name."""
        return self._providers.get(name)

    def get_available_providers(self) -> Dict[str, object]:
        """Get all available and enabled providers."""
        enabled_configs = self.config_manager.get_enabled_providers()
        return {
            name: provider
            for name, provider in self._providers.items()
            if name in enabled_configs and provider.is_available()
        }

    def get_selected_provider(self) -> Optional[object]:
        """Get the currently selected provider."""
        selected_name = self.config_manager.get_selected_provider()
        if selected_name:
            return self.get_provider(selected_name)
        return None

    def set_selected_provider(self, provider_name: str) -> bool:
        """Set the selected provider."""
        if provider_name not in self._providers:
            return False

        return self.config_manager.set_selected_provider(provider_name)

    def execute_prompt_with_provider(
        self, provider_name: str, project_path: str, prompt: str
    ) -> Dict[str, Any]:
        """Execute a prompt using a specific provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            return {
                "success": False,
                "error": f"Provider '{provider_name}' not found",
                "output": "",
            }

        if not provider.is_available():
            return {
                "success": False,
                "error": f"Provider '{provider_name}' is not available",
                "output": "",
            }

        return provider.execute_prompt(project_path, prompt)

    def execute_prompt_with_selected_provider(
        self, project_path: str, prompt: str
    ) -> Dict[str, Any]:
        """Execute a prompt using the currently selected provider."""
        provider = self.get_selected_provider()
        if not provider:
            return {
                "success": False,
                "error": "No provider selected or selected provider not available",
                "output": "",
            }

        return provider.execute_prompt(project_path, prompt)

    def execute_multiple_prompts_parallel(
        self, project_prompts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple prompts in parallel using the selected provider.

        Args:
            project_prompts: List of dicts containing 'project_path' and 'prompt' keys

        Returns:
            List of execution results in the same order as input
        """
        provider = self.get_selected_provider()
        if not provider:
            return [
                {
                    "success": False,
                    "error": "No provider selected or selected provider not available",
                    "output": "",
                    "project_path": prompt_data.get("project_path", ""),
                }
                for prompt_data in project_prompts
            ]

        # Use ThreadPoolExecutor for parallel execution
        def execute_single_prompt(prompt_data):
            project_path = prompt_data.get("project_path")
            prompt = prompt_data.get("prompt")

            if not project_path or not prompt:
                return {
                    "success": False,
                    "error": "Missing project_path or prompt in data",
                    "output": "",
                    "project_path": project_path or "",
                }

            result = provider.execute_prompt(project_path, prompt)
            result["project_path"] = project_path
            result["prompt"] = prompt
            return result

        # Execute all prompts in parallel
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(project_prompts), 10)
        ) as executor:
            # Submit all tasks immediately for parallel execution
            future_to_index = {
                executor.submit(execute_single_prompt, prompt_data): i
                for i, prompt_data in enumerate(project_prompts)
            }

            # Collect results in order
            results = [None] * len(project_prompts)
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    results[index] = {
                        "success": False,
                        "error": f"Unexpected error during execution: {str(e)}",
                        "output": "",
                        "project_path": project_prompts[index].get("project_path", ""),
                        "prompt": project_prompts[index].get("prompt", ""),
                    }

            return results

    def list_providers_info(self) -> List[Dict[str, Any]]:
        """Get information about all providers."""
        return [provider.get_provider_info() for provider in self._providers.values()]

    def prompt_user_for_provider_selection(self) -> Optional[str]:
        """Prompt user to select a provider (for CLI usage)."""
        available_providers = self.get_available_providers()

        if not available_providers:
            print("No external agent providers are available.")
            return None

        print("\nAvailable external agent providers:")
        provider_list = list(available_providers.keys())

        for i, name in enumerate(provider_list, 1):
            provider = available_providers[name]
            print(f"{i}. {name} - {provider.config.description}")

        while True:
            try:
                choice = input(f"\nSelect provider (1-{len(provider_list)}): ").strip()
                index = int(choice) - 1

                if 0 <= index < len(provider_list):
                    selected_provider = provider_list[index]

                    # Set as selected provider
                    if self.set_selected_provider(selected_provider):
                        print(f"Selected provider: {selected_provider}")
                        return selected_provider
                    else:
                        print("Failed to save provider selection.")
                        return None
                else:
                    print("Invalid selection. Please try again.")

            except (ValueError, KeyboardInterrupt):
                print("\nProvider selection cancelled.")
                return None

    def ensure_provider_selected(self) -> bool:
        """Ensure a provider is selected, prompt user if not."""
        selected = self.config_manager.get_selected_provider()

        if selected and selected in self.get_available_providers():
            return True

        # No provider selected or selected provider not available
        print("No external agent provider is configured.")
        selected = self.prompt_user_for_provider_selection()

        return selected is not None

    def get_running_agent_sessions(self) -> List[Dict[str, Any]]:
        """Get information about all running agent sessions."""
        return TerminalSessionManager.get_running_processes()

    def monitor_agent_session(
        self, session_id: str, duration: float = 5.0
    ) -> Dict[str, Any]:
        """Monitor output from a specific agent session."""
        return TerminalSessionManager.monitor_session_output(session_id, duration)

    def list_all_agent_sessions(self) -> List[Dict[str, Any]]:
        """List all agent terminal sessions."""
        all_sessions = TerminalSessionManager.list_sessions()
        # Filter for agent sessions (those with descriptions containing "Agent")
        agent_sessions = [
            session
            for session in all_sessions
            if "Agent" in session.get("description", "")
        ]
        return agent_sessions

    def close_agent_session(self, session_id: str) -> bool:
        """Close a specific agent session."""
        return TerminalSessionManager.close_session(session_id)


# Global instance
_agent_provider_manager = None


def get_agent_provider_manager() -> AgentProviderManager:
    """Get the global agent provider manager instance."""
    global _agent_provider_manager
    if _agent_provider_manager is None:
        _agent_provider_manager = AgentProviderManager()
    return _agent_provider_manager
