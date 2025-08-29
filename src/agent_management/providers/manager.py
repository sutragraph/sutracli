"""
Manager for external agent providers.
"""

from typing import Dict, Any, Optional, List
from .config import AgentProviderConfig, get_provider_config_manager
from .rovodev import RovodevProvider
from .gemini import GeminiProvider


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
    
    def execute_prompt_with_provider(self, provider_name: str, project_path: str, prompt: str) -> Dict[str, Any]:
        """Execute a prompt using a specific provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            return {
                "success": False,
                "error": f"Provider '{provider_name}' not found",
                "output": ""
            }
        
        if not provider.is_available():
            return {
                "success": False,
                "error": f"Provider '{provider_name}' is not available",
                "output": ""
            }
        
        return provider.execute_prompt(project_path, prompt)
    
    def execute_prompt_with_selected_provider(self, project_path: str, prompt: str) -> Dict[str, Any]:
        """Execute a prompt using the currently selected provider."""
        provider = self.get_selected_provider()
        if not provider:
            return {
                "success": False,
                "error": "No provider selected or selected provider not available",
                "output": ""
            }
        
        return provider.execute_prompt(project_path, prompt)
    
    def list_providers_info(self) -> List[Dict[str, Any]]:
        """Get information about all providers."""
        return [
            provider.get_provider_info() 
            for provider in self._providers.values()
        ]
    
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


# Global instance
_agent_provider_manager = None


def get_agent_provider_manager() -> AgentProviderManager:
    """Get the global agent provider manager instance."""
    global _agent_provider_manager
    if _agent_provider_manager is None:
        _agent_provider_manager = AgentProviderManager()
    return _agent_provider_manager