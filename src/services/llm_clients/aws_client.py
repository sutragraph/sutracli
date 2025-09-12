import json
import boto3
import time
from loguru import logger
from typing import List, Dict, Any, Union
from botocore.exceptions import ClientError
from .llm_client_base import LLMClientBase, TokenUsage, LLMResponse
from config import config


class AWSClient(LLMClientBase):
    def __init__(self, model_id=None, region=None):
        super().__init__()
        self.model_id = model_id or config.llm.aws.model_id
        self.region = region or config.llm.aws.region
        self._initialize_bedrock_client()

    def _initialize_bedrock_client(self):
        try:
            self.bedrock_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=config.llm.aws.access_key_id,
                aws_secret_access_key=config.llm.aws.secret_access_key,
            )
            # Only log once per client instance, and be more specific about which model
            logger.debug(f"🤖 Bedrock client initialized successfully for model: {self.model_id} in region: {self.region}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bedrock client: {e}")
            raise

    def call_llm(
        self, system_prompt: str, user_message: str, return_raw: bool = False
    ) -> Union[List[Dict[str, Any]], str]:
        """Call AWS with separate system prompt and user message.

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
        """Call AWS with separate system prompt and user message, returning content and token usage.

        Args:
            system_prompt (str): System prompt
            user_message (str): User message
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            LLMResponse: Response containing both content and token usage information
        """
        max_retries = 9
        retry_delay = 30  # 30 seconds

        for attempt in range(max_retries + 1):
            try:
                # Build request body - only include system prompt if it's not empty
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 65400,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": user_message}],
                        }
                    ],
                }

                # Only add system prompt if it's not empty to avoid validation error
                if system_prompt and system_prompt.strip():
                    request_body["system"] = [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        },
                    ]

                body = json.dumps(request_body)
                logger.debug(
                    f"📦 Sending request to AWS model {self.model_id} with user_message: {user_message}"
                )
                response = self.bedrock_client.invoke_model_with_response_stream(
                    body=body,
                    modelId=self.model_id,
                    accept="application/json",
                    contentType="application/json",
                )

                # Handle streaming response and collect token usage
                raw_response = ""
                input_tokens = 0
                output_tokens = 0
                total_tokens = 0

                for event in response.get("body"):
                    chunk = event.get("chunk")
                    if chunk:
                        chunk_data = json.loads(chunk.get("bytes").decode())
                        if chunk_data["type"] == "content_block_delta":
                            raw_response += chunk_data["delta"]["text"]
                        elif chunk_data["type"] == "message_start":
                            # Extract initial token usage from message start
                            usage = chunk_data.get("message", {}).get("usage", {})
                            if usage:
                                input_tokens = usage.get("input_tokens", 0)
                                # Some responses include output tokens in message_start
                                if "output_tokens" in usage:
                                    output_tokens = usage.get("output_tokens", 0)
                        elif chunk_data["type"] == "message_delta":
                            # Extract updated token usage from message delta
                            usage = chunk_data.get("usage", {})
                            if usage:
                                output_tokens = usage.get("output_tokens", output_tokens)
                        elif chunk_data["type"] == "message_stop":
                            # Extract final token counts from invocation metrics (most accurate)
                            metrics = chunk_data.get("amazon-bedrock-invocationMetrics", {})
                            if metrics:
                                input_tokens = metrics.get("inputTokenCount", input_tokens)
                                output_tokens = metrics.get("outputTokenCount", output_tokens)

                # Calculate total tokens
                total_tokens = input_tokens + output_tokens

                # Create token usage object if we have any token information
                token_usage = None
                if input_tokens > 0 or output_tokens > 0:
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

                print()
                logger.debug(f"📥 Received response from AWS model: {raw_response}")

                # Return content based on return_raw parameter
                if return_raw:
                    content = raw_response
                else:
                    content = self.parse_xml_response(raw_response)

                return LLMResponse(content=content, token_usage=token_usage)

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "ThrottlingException" and attempt < max_retries:
                    logger.warning(
                        f"⚠️  Throttling exception encountered (attempt {attempt + 1}/{max_retries + 1}). "
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
