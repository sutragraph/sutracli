import requests
from loguru import logger
from typing import List, Dict, Any, Union
from .llm_client_base import LLMClientBase, TokenUsage, LLMResponse
from config import config
from ..auth.token_manager import get_token_manager


class SuperLLMClient(LLMClientBase):
    """
    SuperLLM client that communicates with the SuperLLM API server.

    This client requires a Firebase authentication token that users obtain
    from the SuperLLM web interface. The token is used to authenticate
    API requests to the SuperLLM server.
    """

    def __init__(self):
        """Initialize the SuperLLM client with configuration."""
        super().__init__()
        # Load configuration
        if hasattr(config.llm, "superllm") and config.llm.superllm:
            self.api_endpoint = config.llm.superllm.api_endpoint
            self.default_model = config.llm.superllm.default_model
            self.default_provider = config.llm.superllm.default_provider
            config_token = config.llm.superllm.firebase_token
        else:
            # Use defaults if no configuration
            self.api_endpoint = "http://localhost:8000"
            self.default_model = "gpt-3.5-turbo"
            self.default_provider = "openai"
            config_token = ""

        if not self.api_endpoint:
            raise ValueError(
                "SuperLLM API endpoint must be configured in JSON config for SuperLLMClient."
            )

        # Try to get token from secure storage first, then fall back to config
        token_manager = get_token_manager()
        self.firebase_token = token_manager.get_token("superllm")

        if not self.firebase_token and config_token:
            # Use token from config and store it securely
            self.firebase_token = config_token
            token_manager.store_token(
                "superllm",
                config_token,
                {"api_endpoint": self.api_endpoint, "source": "config_migration"},
            )
            logger.info("Migrated Firebase token from config to secure storage")

        if not self.firebase_token:
            logger.warning(
                "SuperLLM Firebase token not found. "
                "Please run 'sutra auth login' to authenticate with SuperLLM."
            )

        if not self.firebase_token:
            raise ValueError(
                "SuperLLM Firebase token not found. "
                "Please run 'sutra auth login' to authenticate with SuperLLM."
            )

        logger.info("🚀 SuperLLM client initialized successfully")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.firebase_token}",
            "Content-Type": "application/json",
        }

    def _refresh_token(self) -> bool:
        """
        Attempt to refresh the Firebase token from storage.

        Returns:
            True if token was refreshed, False otherwise
        """
        token_manager = get_token_manager()
        new_token = token_manager.get_token("superllm")

        if new_token and new_token != self.firebase_token:
            self.firebase_token = new_token
            logger.info("Firebase token refreshed from storage")
            return True

        return False

    def call_llm(self, system_prompt: str, user_message: str, return_raw: bool = False) -> Union[List[Dict[str, Any]], str]:
        """
        Call the SuperLLM API to generate a response with separate system and user messages.

        Args:
            system_prompt: The system prompt for the LLM
            user_message: The user message for the LLM
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            Union[List[Dict[str, Any]], str]: Parsed XML elements or raw response text

        Raises:
            Exception: If the API call fails
        """
        # Use the new method with usage tracking and just return the content
        response = self.call_llm_with_usage(system_prompt, user_message, return_raw)
        return response.content

    def call_llm_with_usage(
        self, system_prompt: str, user_message: str, return_raw: bool = False
    ) -> LLMResponse:
        """
        Call the SuperLLM API and return both content and token usage information.

        Args:
            system_prompt: The system prompt for the LLM
            user_message: The user message for the LLM
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            LLMResponse: Response containing both content and token usage information

        Raises:
            Exception: If the API call fails
        """
        headers = self._get_headers()

        # Prepare the request payload with system and user messages
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "model": self.default_model,
            "provider": self.default_provider,
        }

        response_data = self._make_api_call(payload, headers)

        # Extract content and token usage from response
        if isinstance(response_data, dict):
            raw_response = response_data.get("content", str(response_data))

            # Check for token usage in response
            token_usage = None
            if "usage" in response_data:
                usage = response_data["usage"]
                token_usage = TokenUsage(
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0)
                )
            elif "token_usage" in response_data:
                usage = response_data["token_usage"]
                token_usage = TokenUsage(
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0)
                )
        else:
            raw_response = str(response_data)
            token_usage = None

        if token_usage:
            print(
                f"🔢 Token usage - Input: {token_usage.input_tokens}, "
                f"Output: {token_usage.output_tokens}, "
                f"Total: {token_usage.total_tokens}"
            )

        # Return content based on return_raw parameter
        if return_raw:
            content = raw_response
        else:
            content = self.parse_xml_response(raw_response)

        return LLMResponse(content=content, token_usage=token_usage)

    def call_llm_single(self, prompt: str, return_raw: bool = False) -> Union[List[Dict[str, Any]], str]:
        """
        Call the SuperLLM API to generate a response with a single prompt.

        Args:
            prompt: The input prompt for the LLM
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            Union[List[Dict[str, Any]], str]: Parsed XML elements or raw response text

        Raises:
            Exception: If the API call fails
        """
        headers = self._get_headers()

        # Prepare the request payload in SuperLLM API format
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": self.default_model,
            "provider": self.default_provider,
        }

        raw_response = self._make_api_call(payload, headers)

        # Return raw response or parse XML based on return_raw parameter
        if return_raw:
            return raw_response
        else:
            return self.parse_xml_response(raw_response)

    def _make_api_call(self, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
        """
        Make an API call to the SuperLLM server.

        Args:
            payload: The request payload
            headers: The request headers

        Returns:
            str: The response content

        Raises:
            Exception: If the API call fails
        """
        try:
            response = requests.post(
                f"{self.api_endpoint}/chat/completions",
                json=payload,
                headers=headers,
                timeout=300,  # 5 minute timeout
            )

            if response.status_code == 200:
                response_data = response.json()

                # Handle different response formats
                if "choices" in response_data and response_data["choices"]:
                    content = response_data["choices"][0]["message"]["content"]
                elif "content" in response_data:
                    content = response_data["content"]
                else:
                    content = str(response_data)

                # Return the full response data for token tracking
                if isinstance(response_data, dict):
                    response_data["content"] = content
                    return response_data
                else:
                    return content
            else:
                logger.error(f"SuperLLM API error: {response.status_code} - {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            if e.response.status_code == 401:
                # Try to refresh token once
                if self._refresh_token():
                    headers = self._get_headers()
                    return self._make_api_call(payload, headers)
                else:
                    raise ValueError(
                        "SuperLLM authentication failed. "
                        "Please run 'sutra auth login' to re-authenticate."
                    )
            else:
                logger.error(f"SuperLLM API request failed: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error calling SuperLLM API: {e}")
            raise
