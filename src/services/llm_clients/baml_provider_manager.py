"""
BAML Provider Manager

This module provides dynamic function calling based on the provider configuration.
Uses the existing config system to determine which provider to use and calls the
appropriate BAML function with the correct provider prefix.
"""

import os
from typing import Any, Dict
import asyncio

from baml_client import b
from config import config


class BAMLProviderManager:
    """Manages BAML provider selection and dynamic function calling using existing config system."""
    
    # Provider mapping from config to BAML function prefix
    PROVIDER_MAPPING = {
        "aws": "Aws",
        "openai": "Gpt",
        "anthropic": "Anthropic",
        "gcp": "Gemini"
    }
    
    def __init__(self):
        """Initialize the provider manager using existing config system."""
        self.provider = config.llm.provider.lower()
    
    def get_function_name(self, base_function_name: str) -> str:
        """Get the provider-specific function name."""
        provider_prefix = self.PROVIDER_MAPPING[self.provider]
        return f"{provider_prefix}{base_function_name}"
    
    async def call_function(self, function_name: str, **kwargs) -> Any:
        """Dynamically call a BAML function based on provider configuration."""
        # Get the provider-specific function name
        full_function_name = self.get_function_name(function_name)
        
        print(f"Calling BAML function: {full_function_name} (provider: {self.provider})")
        
        # Get the function from BAML client
        if not hasattr(b, full_function_name):
            raise AttributeError(f"Function {full_function_name} not found in BAML client")
        
        baml_function = getattr(b, full_function_name)
        
        # Call the function with provided arguments
        try:
            result = await baml_function(**kwargs)
            return result
        except Exception as e:
            raise RuntimeError(f"Error calling {full_function_name}: {e}")
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get information about the current provider setup."""
        return {
            "provider": self.provider,
            "function_prefix": self.PROVIDER_MAPPING[self.provider]
        }
