"""
BAML Utilities

Utilities for calling BAML functions with dynamic function resolution and provider management.
"""

import logging
from typing import Any
from baml_client.sync_client import b as baml
from config import config

logger = logging.getLogger(__name__)

PROVIDER_MAPPING = {
    "aws": "Aws",
    "openai": "ChatGPT",
    "anthropic": "Anthropic",
    "gcp": "Gemini",
}


def call_baml(function_name: str, **kwargs) -> Any:
    """
    Universal utility function to dynamically call BAML functions.
    
    This function handles:
    - Automatic provider detection from config
    - Automatic provider-to-prefix mapping
    - Dynamic function name construction with prefix
    - Function existence validation
    - Logging with role-based caching and token tracking
    - Function execution with provided arguments
    
    Args:
        function_name: Base name of the function (e.g., "ConnectionMatching")
        **kwargs: Arguments to pass to the BAML function
        
    Returns:
        Response from the BAML function
        
    Raises:
        AttributeError: If the function doesn't exist in BAML client
        ImportError: If baml module cannot be imported
        ValueError: If provider is not supported
    """
    provider = config.llm.provider.lower()
    
    # Get function prefix from provider mapping
    if provider not in PROVIDER_MAPPING:
        available_providers = list(PROVIDER_MAPPING.keys())
        raise ValueError(
            f"Provider '{provider}' not supported. Available providers: {available_providers}"
        )
    
    function_prefix = PROVIDER_MAPPING[provider]
    
    # Construct the full function name
    full_function_name = f"{function_prefix}{function_name}"
    
    # Log the function call with provider info
    logger.info(
        f"🤖 Calling BAML {full_function_name} (provider: {provider})"
    )
  
    baml_function = getattr(baml, full_function_name)
    
    response = baml_function(**kwargs)
    return response
