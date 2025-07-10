import json
import boto3
import time
from loguru import logger
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from .llm_client_base import LLMClientBase
from ...config import config


class AWSClient(LLMClientBase):
    def __init__(self, model_id=None, region=None):
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
            logger.info("🤖 Bedrock client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bedrock client: {e}")
            raise

    def call_llm(self, system_prompt: str, user_message: str) -> List[Dict[str, Any]]:
        """Call AWS with separate system prompt and user message."""
        max_retries = 5
        retry_delay = 30  # 30 seconds

        for attempt in range(max_retries + 1):
            try:
                body = json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 65000,
                        "system": [
                            {
                                "type": "text",
                                "text": system_prompt,
                                "cache_control": {"type": "ephemeral"},
                            },
                        ],
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"type": "text", "text": user_message}],
                            }
                        ],
                    }
                )
                logger.debug(
                    f"📦 Sending request to AWS model {self.model_id} with body: {body}"
                )
                response = self.bedrock_client.invoke_model_with_response_stream(
                    body=body,
                    modelId=self.model_id,
                    accept="application/json",
                    contentType="application/json",
                )

                # Handle streaming response
                raw_response = ""
                for event in response.get("body"):
                    chunk = event.get("chunk")
                    if chunk:
                        chunk_data = json.loads(chunk.get("bytes").decode())
                        if chunk_data["type"] == "content_block_delta":
                            raw_response += chunk_data["delta"]["text"]

                logger.debug(f"📥 Received response from AWS model: {raw_response}")
                # Parse XML from the response and return only XML data
                return self.parse_xml_response(raw_response)

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
