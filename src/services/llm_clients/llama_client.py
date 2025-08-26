import os
import sys
import requests
from loguru import logger
from typing import List, Dict, Any, Union
from .llm_client_base import LLMClientBase, TokenUsage, LLMResponse
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from config import config


class LlamaClient(LLMClientBase):
    def __init__(self):
        super().__init__()
        self.model_id = config.llm.llama_model_id
        self.endpoint = config.llm.gcp.llm_endpoint

        # Set up service account path
        if getattr(sys, "frozen", False):
            # Running as PyInstaller executable
            base_dir = sys._MEIPASS
            self.service_account_path = os.path.join(
                base_dir, "certs", "hyra-720a2-07066fb5695a.json"
            )
        else:
            # Running from source
            self.service_account_path = "certs/hyra-720a2-07066fb5695a.json"

        if not self.endpoint:
            raise ValueError(
                "GCP LLM endpoint must be configured in JSON config for LlamaClient."
            )

        if not os.path.exists(self.service_account_path):
            logger.warning(
                f"Service account file not found at: {self.service_account_path}"
            )
            raise ValueError(
                f"Service account file not found: {self.service_account_path}"
            )
        else:
            logger.debug(f"Using service account file: {self.service_account_path}")

    def _get_access_token(self):
        credentials = service_account.Credentials.from_service_account_file(
            self.service_account_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        credentials.refresh(Request())
        return credentials.token

    def call_llm(self, system_prompt: str, user_message: str, return_raw: bool = False) -> Union[List[Dict[str, Any]], str]:
        """Call Llama with separate system prompt and user message.

        Args:
            system_prompt (str): System prompt
            user_message (str): User message
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            Union[List[Dict[str, Any]], str]: Parsed XML elements or raw response text
        """
        # Use the new method with usage tracking and just return the content
        response = self.call_llm_with_usage(system_prompt, user_message, return_raw)
        return response.content

    def call_llm_with_usage(
        self, system_prompt: str, user_message: str, return_raw: bool = False
    ) -> LLMResponse:
        """Call Llama with separate system prompt and user message, returning content and token usage.

        Args:
            system_prompt (str): System prompt
            user_message (str): User message
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            LLMResponse: Response containing both content and token usage information
        """
        access_token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        try:
            response = requests.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_response = data["choices"][0]["message"]["content"]

            # Extract token usage if available
            token_usage = None
            if "usage" in data:
                usage = data["usage"]
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

                token_usage = TokenUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens
                )
                print(
                    f"🔢 Token usage - Input: {input_tokens}, "
                    f"Output: {output_tokens}, "
                    f"Total: {total_tokens}"
                )

            # Return content based on return_raw parameter
            if return_raw:
                content = raw_response
            else:
                content = self.parse_xml_response(raw_response)

            return LLMResponse(content=content, token_usage=token_usage)

        except Exception as e:
            logger.error(f"Llama LLM call with system prompt failed: {e}")
            raise
