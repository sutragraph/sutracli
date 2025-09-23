"""
BAML Service

Generic service for calling BAML functions with dynamic function resolution,
provider management, and proper error handling.
"""

import time

from baml_py import ClientRegistry, Collector
from loguru import logger

from config.settings import (
    get_available_providers,
    get_baml_provider_mapping,
    get_config,
    is_provider_supported,
)

# Global token usage tracking across all calls
_global_token_usage = {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cached_input_tokens": 0,
    "total_calls": 0,
    "call_history": [],  # List of (call_number, function_name, input_tokens, output_tokens)
}


class BAMLService:
    """Generic service for calling BAML functions."""

    def __init__(self):
        """Initialize BAML service."""
        config_obj = get_config(force_reload=True)
        self.provider = config_obj.llm.provider.lower()

        self._validate_provider()

        # Create dynamic client registry instead of using static clients
        self.client_registry = ClientRegistry()
        self._setup_dynamic_client()

        from baml_client.sync_client import b as baml

        self.baml = baml

    def _validate_provider(self):
        """Validate that the configured provider is supported."""
        if not is_provider_supported(self.provider):
            available_providers = get_available_providers()
            raise ValueError(
                f"Provider '{self.provider}' not supported. Available providers: {available_providers}"
            )

    def _setup_dynamic_client(self):
        """Set up dynamic client based on current provider configuration."""
        config_obj = get_config()
        provider = self.provider

        # Get provider config
        provider_config = getattr(config_obj.llm, provider, None)
        if not provider_config:
            raise ValueError(f"No configuration found for provider: {provider}")

        # Get BAML provider mapping from settings
        baml_provider_mapping = get_baml_provider_mapping()
        provider_info = baml_provider_mapping.get(provider)
        if not provider_info:
            raise ValueError(f"Unsupported provider for dynamic client: {provider}")

        baml_provider = provider_info["provider"]
        client_name = provider_info["client_name"]
        options = self._build_client_options(provider, provider_config)

        # Create the dynamic client
        self.client_registry.add_llm_client(
            name=client_name, provider=baml_provider, options=options
        )

        # Set as primary client
        self.client_registry.set_primary(client_name)

        # Check Vertex AI authentication if using vertex_ai provider
        if provider == "vertex_ai":
            self._check_vertex_ai_auth()

    def _build_client_options(self, provider: str, provider_config):
        """Build client options for the given provider."""
        options = {}

        if provider == "aws_bedrock":
            options.update(
                {
                    "access_key_id": provider_config.access_key_id,
                    "secret_access_key": provider_config.secret_access_key,
                    "model": provider_config.model_id,
                    "region": provider_config.region,
                    "inference_configuration": {
                        "temperature": 0.1,
                        "max_tokens": int(provider_config.max_tokens),
                    },
                    "allowed_role_metadata": ["system", "user", "cache_control"],
                }
            )

        elif provider == "anthropic":
            options.update(
                {
                    "api_key": provider_config.api_key,
                    "model": provider_config.model_id,
                    "temperature": 0.1,
                    "max_tokens": int(provider_config.max_tokens),
                    "allowed_role_metadata": ["system", "user", "cache_control"],
                    "headers": {"anthropic-beta": "prompt-caching-2024-07-31"},
                }
            )

        elif provider == "openai":
            options.update(
                {
                    "api_key": provider_config.api_key,
                    "model": provider_config.model_id,
                    "temperature": 0.1,
                    "max_tokens": int(provider_config.max_tokens),
                    "allowed_roles": ["system", "user"],
                }
            )

        elif provider == "google_ai":
            options.update(
                {
                    "api_key": provider_config.api_key,
                    "model": provider_config.model_id,
                    "allowed_roles": ["system", "user"],
                    "generationConfig": {
                        "maxOutputTokens": int(provider_config.max_tokens),
                        "temperature": 0.1,
                    },
                }
            )
            if hasattr(provider_config, "base_url") and provider_config.base_url:
                options["base_url"] = provider_config.base_url

        elif provider == "vertex_ai":
            options.update(
                {
                    "model": provider_config.model_id,
                    "location": provider_config.location,
                    "allowed_roles": ["system", "user"],
                    "generationConfig": {
                        "maxOutputTokens": int(provider_config.max_tokens),
                        "temperature": 0.1,
                    },
                }
            )

        elif provider == "azure_openai":
            options.update(
                {
                    "api_key": provider_config.api_key,
                    "base_url": provider_config.base_url,
                    "api_version": provider_config.api_version,
                    "temperature": 0.1,
                    "max_tokens": int(provider_config.max_tokens),
                    "allowed_roles": ["system", "user"],
                }
            )

        elif provider == "azure_aifoundry":
            options.update(
                {
                    "base_url": provider_config.base_url,
                    "api_key": provider_config.api_key,
                    "max_tokens": int(provider_config.max_tokens),
                    "allowed_roles": ["system", "user"],
                }
            )

        elif provider == "openrouter":
            options.update(
                {
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key": provider_config.api_key,
                    "model": provider_config.model_id,
                    "max_tokens": int(provider_config.max_tokens),
                    "allowed_roles": ["system", "user"],
                }
            )
            headers = {}
            if (
                hasattr(provider_config, "http_referer")
                and provider_config.http_referer
            ):
                headers["HTTP-Referer"] = provider_config.http_referer
            if hasattr(provider_config, "x_title") and provider_config.x_title:
                headers["X-Title"] = provider_config.x_title
            if headers:
                options["headers"] = headers

        return options

    def _check_vertex_ai_auth(self):
        """Check Vertex AI authentication."""
        try:
            from cli.setup import _check_vertex_ai_auth

            _check_vertex_ai_auth()
        except ImportError:
            # If setup module not available, skip check
            pass

    def _get_full_function_name(self, base_function_name: str) -> str:
        """Get full BAML function name with provider prefix."""
        baml_provider_mapping = get_baml_provider_mapping()
        function_prefix = baml_provider_mapping[self.provider]["client_name"]
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
        **kwargs,
    ):
        """
        Call a BAML function with retry mechanism and token tracking.

        Args:
            function_name: Base name of the function (e.g., "RoadmapAgent")
            max_retries: Maximum number of retry attempts (default: 9)
            retry_delay: Delay between retries in seconds (default: 30)
            **kwargs: Arguments to pass to the BAML function

        Raises:
            AttributeError: If the function doesn't exist
            Exception: If all retry attempts fail
        """
        # Get full function name with provider prefix
        full_function_name = self._get_full_function_name(function_name)

        # Get BAML function
        baml_function = self._get_baml_function(full_function_name)

        # Token usage tracking
        total_input_tokens = 0
        total_output_tokens = 0
        total_cached_input_tokens = 0

        for attempt in range(max_retries + 1):
            try:
                # Create BAML collector for this attempt
                collector = Collector(
                    name=f"{full_function_name}-attempt-{attempt + 1}"
                )

                # Call BAML function with collector and client registry
                response = baml_function(
                    **kwargs,
                    baml_options={
                        "collector": collector,
                        "client_registry": self.client_registry,
                    },
                )

                # Debug log raw response and user prompts if collector has the data
                try:
                    if collector.last and collector.last.calls:
                        # Add visual separator for debug section
                        logger.debug("=" * 80)

                        # Get the HTTP request body which contains the prompt
                        request_body = collector.last.calls[-1].http_request.body.json()

                        logger.debug("-" * 50)
                        logger.debug(f"📝 USER PROMPTS ({full_function_name}):")
                        logger.debug("-" * 50)

                        if "messages" in request_body:
                            # OpenAI, Anthropic, etc. format
                            messages = request_body["messages"]
                            # Filter for just user messages
                            user_messages = [
                                msg for msg in messages if msg["role"] == "user"
                            ]
                            for i, msg in enumerate(user_messages):
                                logger.debug(f"🔹 User prompt {i + 1}:")
                                logger.debug(f"   {msg['content'][0]['text']}")
                                logger.debug("")
                        elif "contents" in request_body:
                            # Google AI (Gemini) format
                            contents = request_body["contents"]
                            # Filter for just user messages
                            user_contents = [
                                content
                                for content in contents
                                if content["role"] == "user"
                            ]
                            for i, content in enumerate(user_contents):
                                logger.debug(f"🔹 User prompt {i + 1}:")
                                logger.debug(f"   {content['parts'][0]['text']}")
                                logger.debug("")
                        else:
                            # Fallback: log entire request body
                            logger.debug(f"{request_body}")
                            logger.debug("")

                        # Log raw LLM response
                        if (
                            hasattr(collector.last, "raw_llm_response")
                            and collector.last.raw_llm_response
                        ):
                            logger.debug("-" * 50)
                            logger.debug("🤖 RAW LLM RESPONSE:")
                            logger.debug("-" * 50)
                            logger.debug(f"{collector.last.raw_llm_response}")
                            logger.debug("")
                        logger.debug("=" * 80)

                except Exception as e:
                    logger.debug("=" * 80)
                    logger.debug(
                        f"❌ Could not extract raw response/prompts for {full_function_name}: {e}"
                    )
                    logger.debug("=" * 80)

                # Extract actual token usage from BAML collector
                actual_input_tokens = (
                    getattr(collector.last.usage, "input_tokens", None) or 0
                )
                actual_output_tokens = (
                    getattr(collector.last.usage, "output_tokens", None) or 0
                )
                cached_input_tokens = (
                    getattr(collector.last.usage, "cached_input_tokens", None) or 0
                )

                # Track token usage
                total_input_tokens += actual_input_tokens
                total_output_tokens += actual_output_tokens
                total_cached_input_tokens += cached_input_tokens

                # Update global token usage tracking
                _global_token_usage["total_input_tokens"] += actual_input_tokens
                _global_token_usage["total_output_tokens"] += actual_output_tokens
                _global_token_usage["total_cached_input_tokens"] += cached_input_tokens
                _global_token_usage["total_calls"] += 1

                # Get current call number
                call_number = _global_token_usage["total_calls"]

                # Add to call history
                _global_token_usage["call_history"].append(
                    (
                        call_number,
                        full_function_name,
                        actual_input_tokens,
                        actual_output_tokens,
                        cached_input_tokens,
                    )
                )

                # Log token usage for this call with call counter
                print(
                    f"🔢 Token Usage #{call_number} - "
                    f"Input: {actual_input_tokens}, Output: {actual_output_tokens}, "
                    f"Cached: {cached_input_tokens}, "
                    f"Total: {actual_input_tokens + actual_output_tokens}"
                )

                # Log cumulative token usage across all calls
                cumulative_total = (
                    _global_token_usage["total_input_tokens"]
                    + _global_token_usage["total_output_tokens"]
                )
                print(
                    f"📊 Cumulative Token Usage (Total {call_number} calls) - "
                    f"Input: {_global_token_usage['total_input_tokens']}, "
                    f"Output: {_global_token_usage['total_output_tokens']}, "
                    f"Cached: {_global_token_usage['total_cached_input_tokens']}, "
                    f"Total: {cumulative_total}"
                )

                return response

            except Exception as e:
                error_msg = f"Error calling BAML {full_function_name}: {str(e)}"

                logger.debug(error_msg)

                if attempt < max_retries:
                    print(
                        f"⚠️  Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    # All retries exhausted
                    final_error_msg = f"BAML {full_function_name} failed after {max_retries + 1} attempts"
                    logger.error(final_error_msg)
                    print(f"❌ {final_error_msg}")
                    raise Exception(f"{final_error_msg}. Last error: {str(e)}") from e

        # This should never be reached, but just in case
        raise Exception(
            f"Unexpected error in retry logic for BAML {full_function_name}"
        )

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
        baml_provider_mapping = get_baml_provider_mapping()
        prefix = baml_provider_mapping[self.provider]["client_name"]
        all_functions = [attr for attr in dir(self.baml) if not attr.startswith("_")]

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
        baml_provider_mapping = get_baml_provider_mapping()
        return {
            "provider": self.provider,
            "prefix": baml_provider_mapping[self.provider]["client_name"],
            "available_providers": get_available_providers(),
        }
