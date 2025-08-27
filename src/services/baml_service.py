"""
BAML Service

Generic service for calling BAML functions with dynamic function resolution,
provider management, and proper error handling.
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


class BAMLService:
    """Generic service for calling BAML functions."""

    PROVIDER_MAPPING = {
        "aws": "Aws",
        "openai": "ChatGPT",
        "anthropic": "Anthropic",
        "gcp": "Gemini",
    }

    def __init__(self):
        """Initialize BAML service."""
        self.provider = config.llm.provider.lower()
        self._validate_provider()

        # Import BAML client
        try:
            from baml_client.sync_client import b as baml
            self.baml = baml
        except ImportError as e:
            logger.error(f"Failed to import BAML client: {e}")
            raise ImportError("BAML client is required for BAMLService") from e

    def _validate_provider(self):
        """Validate that the configured provider is supported."""
        if self.provider not in self.PROVIDER_MAPPING:
            available_providers = list(self.PROVIDER_MAPPING.keys())
            raise ValueError(
                f"Provider '{self.provider}' not supported. Available providers: {available_providers}"
            )

    def _get_full_function_name(self, base_function_name: str) -> str:
        """Get full BAML function name with provider prefix."""
        function_prefix = self.PROVIDER_MAPPING[self.provider]
        return f"{function_prefix}{base_function_name}"

    def _get_baml_function(self, full_function_name: str):
        """Get BAML function by name."""
        if not hasattr(self.baml, full_function_name):
            raise AttributeError(f"BAML function '{full_function_name}' not found")
        return getattr(self.baml, full_function_name)

    def call(
        self,
        function_name: str,
        max_retries: int = 9,
        retry_delay: int = 30,
        **kwargs
    ) -> BAMLResponse:
        """
        Call a BAML function with retry mechanism and token tracking.

        Args:
            function_name: Base name of the function (e.g., "RoadmapAgent")
            max_retries: Maximum number of retry attempts (default: 9)
            retry_delay: Delay between retries in seconds (default: 30)
            **kwargs: Arguments to pass to the BAML function

        Returns:
            BAMLResponse with content and token usage

        Raises:
            AttributeError: If the function doesn't exist
            Exception: If all retry attempts fail
        """
        # Get full function name with provider prefix
        full_function_name = self._get_full_function_name(function_name)

        # Log the function call
        logger.info(f"🤖 Calling BAML {full_function_name} (provider: {self.provider})")

        # Get BAML function
        baml_function = self._get_baml_function(full_function_name)

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

                # Extract token usage from BAML collector
                actual_input_tokens = (
                    getattr(collector.last.usage, "input_tokens", 0) or
                    getattr(collector.last.usage, "prompt_tokens", 0)
                ) if collector.last and hasattr(collector.last, 'usage') else 0

                actual_output_tokens = (
                    getattr(collector.last.usage, "output_tokens", 0) or
                    getattr(collector.last.usage, "completion_tokens", 0)
                ) if collector.last and hasattr(collector.last, 'usage') else 0

                # Track token usage
                total_input_tokens += actual_input_tokens
                total_output_tokens += actual_output_tokens
                successful_attempt = attempt + 1

                # Log token usage
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

                # Log success on retry
                if attempt > 0:
                    logger.info(f"✅ BAML {full_function_name} succeeded on attempt {attempt + 1}")

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
                print(f"❌ {error_msg}")
                logger.error(error_msg)

                if attempt < max_retries:
                    logger.warning(
                        f"⚠️  BAML call failed (attempt {attempt + 1}/{max_retries + 1}). "
                        f"Retrying in {retry_delay} seconds..."
                    )
                    print(f"⚠️  Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(retry_delay)
                    continue
                else:
                    # All retries exhausted
                    final_error_msg = f"BAML {full_function_name} failed after {max_retries + 1} attempts"
                    logger.error(final_error_msg)
                    print(f"❌ {final_error_msg}")
                    raise Exception(f"{final_error_msg}. Last error: {str(e)}") from e

        # This should never be reached
        raise Exception(f"Unexpected error in retry logic for BAML {full_function_name}")

    def function_exists(self, function_name: str) -> bool:
        """
        Check if a BAML function exists.

        Args:
            function_name: Base name of the function

        Returns:
            True if function exists, False otherwise
        """
        try:
            full_function_name = self._get_full_function_name(function_name)
            return hasattr(self.baml, full_function_name)
        except Exception:
            return False

    def list_available_functions(self) -> list[str]:
        """
        List all available BAML functions with the current provider prefix.

        Returns:
            List of available function names (without prefix)
        """
        prefix = self.PROVIDER_MAPPING[self.provider]
        all_functions = [attr for attr in dir(self.baml) if not attr.startswith('_')]

        # Filter functions that start with our provider prefix
        prefixed_functions = [f for f in all_functions if f.startswith(prefix)]

        # Remove the prefix to get base function names
        base_functions = [f[len(prefix):] for f in prefixed_functions]

        return base_functions

    def get_provider_info(self) -> dict[str, str]:
        """
        Get information about the current provider configuration.

        Returns:
            Dictionary with provider information
        """
        return {
            "provider": self.provider,
            "prefix": self.PROVIDER_MAPPING[self.provider],
            "available_providers": list(self.PROVIDER_MAPPING.keys())
        }
