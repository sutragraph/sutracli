import anthropic
import time
from loguru import logger
from typing import List, Dict, Any, Union
from .llm_client_base import LLMClientBase
from config import config


class AnthropicClient(LLMClientBase):
    def __init__(self, model_id=None):
        super().__init__()
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

    def call_llm(
        self, system_prompt: str, user_message: str, return_raw: bool = False
    ) -> Union[List[Dict[str, Any]], str]:
        """Call Anthropic with separate system prompt and user message.

        Args:
            system_prompt (str): System prompt
            user_message (str): User message
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            Union[List[Dict[str, Any]], str]: Parsed XML elements or raw response text
        """
        max_retries = 5
        retry_delay = 30  # 30 seconds

        for attempt in range(max_retries + 1):
            try:
                stream = self.client.messages.create(
                    model=self.model_id,
                    max_tokens=64000,
                    stream=True,
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

                # Handle streaming response
                raw_response = ""
                for chunk in stream:
                    if chunk.type == "content_block_delta":
                        text = getattr(chunk.delta, "text", None)
                        if text:
                            raw_response += text

                logger.debug(
                    f"📥 Received response from Anthropic model: {raw_response}"
                )
                # Return raw response or parse XML based on return_raw parameter
                if return_raw:
                    return raw_response
                else:
                    return self.parse_xml_response(raw_response)

            except anthropic.RateLimitError as e:
                if attempt < max_retries:
                    logger.warning(
                        f"⚠️  Rate limit exception encountered (attempt {attempt + 1}/{max_retries + 1}). "
                        f"Waiting {retry_delay} seconds before retrying..."
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"LLM call with system prompt failed: {e}")
                    raise
            except Exception as e:
                logger.error(f"LLM call with system prompt failed: {e}")
                raise

        if return_raw:
            return ""
        else:
            return []
