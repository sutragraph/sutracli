import anthropic
from loguru import logger
from typing import List, Dict, Any
from .llm_client_base import LLMClientBase
from ...config import config


class AnthropicClient(LLMClientBase):
    def __init__(self, model_id=None):
        self.model_id = model_id or config.llm.anthropic.model_id
        self.api_key = config.llm.anthropic.api_key
        self._initialize_client()

    def _initialize_client(self):
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("🤖 Anthropic client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Anthropic client: {e}")
            raise

    def call_llm(self, system_prompt: str, user_message: str) -> List[Dict[str, Any]]:
        """Call Anthropic with separate system prompt and user message."""
        try:
            message = self.client.messages.create(
                model=self.model_id,
                max_tokens=30000,
                stream=False,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            )
            raw_response = message.content[0].text

            # Parse XML from the response and return only XML data
            return self.parse_xml_response(raw_response)
        except Exception as e:
            logger.error(f"LLM call with system prompt failed: {e}")
            raise
