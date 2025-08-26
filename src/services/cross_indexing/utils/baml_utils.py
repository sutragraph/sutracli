"""
BAML Utilities

Utilities for calling BAML functions with dynamic function resolution and provider management.
"""
from loguru import logger
import time
from typing import Any, Optional, NamedTuple
from config import config
from baml_py import Collector


class BAMLTokenUsage(NamedTuple):
    """Token usage information from BAML calls."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    retry_count: int
    total_attempts: int


class BAMLResponse(NamedTuple):
    """Response from BAML call including content and token usage."""

    content: Any
    token_usage: Optional[BAMLTokenUsage]


PROVIDER_MAPPING = {
    "aws": "Aws",
    "openai": "ChatGPT",
    "anthropic": "Anthropic",
    "gcp": "Gemini",
}


def call_baml(function_name: str, **kwargs) -> Any:
    """
    Universal utility function to dynamically call BAML functions with retry mechanism and token tracking.

    This function handles:
    - Automatic provider detection from config
    - Automatic provider-to-prefix mapping
    - Dynamic function name construction with prefix
    - Function existence validation
    - Logging with role-based caching and token tracking
    - Function execution with provided arguments
    - Retry mechanism with 10 attempts at 30-second intervals for any error
    - Token usage collection using BAML's built-in Collector (with fallback estimation)

    Args:
        function_name: Base name of the function (e.g., "ConnectionMatching")
        **kwargs: Arguments to pass to the BAML function

    Returns:
        Response from the BAML function

    Raises:
        AttributeError: If the function doesn't exist in BAML client
        ImportError: If baml module cannot be imported
        ValueError: If provider is not supported
        Exception: If all retry attempts fail
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

    from baml_client.sync_client import b as baml

    baml_function = getattr(baml, full_function_name)

    # Retry configuration
    max_retries = 9
    retry_delay = 30  # 30 seconds

    # Token usage tracking
    total_input_tokens = 0
    total_output_tokens = 0
    successful_attempt = 0

    for attempt in range(max_retries + 1):
        try:
            # Create BAML collector for this attempt
            collector = Collector(name=f"{full_function_name}-attempt-{attempt + 1}")

            # Call BAML function with collector
            response = baml_function(**kwargs, baml_options={"collector": collector})

            # Extract actual token usage from BAML collector
            actual_input_tokens = getattr(
                collector.last.usage, "input_tokens", 0
            ) or getattr(collector.last.usage, "prompt_tokens", 0)
            actual_output_tokens = getattr(
                collector.last.usage, "output_tokens", 0
            ) or getattr(collector.last.usage, "completion_tokens", 0)

            # Track token usage
            total_input_tokens += actual_input_tokens
            total_output_tokens += actual_output_tokens
            successful_attempt = attempt + 1

            # Log token usage for this call
            print(
                f"🔢 BAML {full_function_name} Token Usage - "
                f"Input: {actual_input_tokens}, Output: {actual_output_tokens}, "
                f"Total: {actual_input_tokens + actual_output_tokens}"
            )

            # Log additional collector information
            if collector.last:
                if hasattr(collector.last, "raw_llm_response"):
                    logger.debug(
                        f"🔍 BAML {full_function_name} Raw Response Length: {len(str(collector.last.raw_llm_response))}"
                    )
                if hasattr(collector.last, "calls") and collector.last.calls:
                    logger.debug(
                        f"🔍 BAML {full_function_name} HTTP Calls: {len(collector.last.calls)}"
                    )

            # If we get here, the call was successful
            if attempt > 0:
                logger.info(
                    f"✅ BAML {full_function_name} succeeded on attempt {attempt + 1}"
                )

            # Create token usage summary
            token_usage = BAMLTokenUsage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                total_tokens=total_input_tokens + total_output_tokens,
                retry_count=attempt,
                total_attempts=successful_attempt,
            )

            return BAMLResponse(content=response, token_usage=token_usage)

        except Exception as e:
            error_msg = f"Error calling BAML {full_function_name}: {str(e)}"

            # Print the error as requested
            print(f"❌ {error_msg}")
            logger.error(error_msg)

            if attempt < max_retries:
                logger.warning(
                    f"⚠️  BAML call failed (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {retry_delay} seconds..."
                )
                print(
                    f"⚠️  Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(retry_delay)
                continue
            else:
                # All retries exhausted
                final_error_msg = (
                    f"BAML {full_function_name} failed after {max_retries + 1} attempts"
                )
                logger.error(final_error_msg)
                print(f"❌ {final_error_msg}")
                raise Exception(f"{final_error_msg}. Last error: {str(e)}") from e

    # This should never be reached, but just in case
    raise Exception(f"Unexpected error in retry logic for BAML {full_function_name}")
