import anthropic
import time
from loguru import logger
from typing import List, Dict, Any, Union
from .llm_client_base import LLMClientBase, TokenUsage, LLMResponse
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
            print("🤖 Anthropic client initialized successfully")
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
        # Use the new method with usage tracking and just return the content
        response = self.call_llm_with_usage(system_prompt, user_message, return_raw)
        return response.content

    def call_llm_with_usage(
        self, system_prompt: str, user_message: str, return_raw: bool = False
    ) -> LLMResponse:
        """Call Anthropic with separate system prompt and user message, returning content and token usage.

        Args:
            system_prompt (str): System prompt
            user_message (str): User message
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            LLMResponse: Response containing both content and token usage information
        """
        max_retries = 5
        retry_delay = 30  # 30 seconds

        for attempt in range(max_retries + 1):
            try:
                # Use streaming to get token usage information and avoid timeout
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

                # Handle streaming response and extract tokens
                raw_response = ""
                input_tokens = 0
                output_tokens = 0

                for chunk in stream:
                    if chunk.type == "content_block_delta":
                        text = getattr(chunk.delta, "text", None)
                        if text:
                            raw_response += text
                    elif chunk.type == "message_start":
                        # Extract initial token usage
                        if hasattr(chunk, 'message') and hasattr(chunk.message, 'usage'):
                            usage = chunk.message.usage
                            input_tokens = getattr(usage, 'input_tokens', 0)
                            output_tokens = getattr(usage, 'output_tokens', 0)
                    elif chunk.type == "message_delta":
                        # Extract final token usage
                        if hasattr(chunk, 'usage'):
                            usage = chunk.usage
                            output_tokens = getattr(usage, 'output_tokens', output_tokens)

                # Create token usage object
                token_usage = None
                if input_tokens > 0 or output_tokens > 0:
                    total_tokens = input_tokens + output_tokens
                    token_usage = TokenUsage(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens
                    )

                print()
                logger.debug(
                    f"📥 Received response from Anthropic model: {raw_response}"
                )

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

        # Fallback return
        if return_raw:
            content = ""
        else:
            content = []
        return LLMResponse(content=content, token_usage=None)
