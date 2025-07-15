import os
from loguru import logger
from typing import List, Dict, Any, Union
from .llm_client_base import LLMClientBase
from google import genai
from config import config
import sys


class GeminiClient(LLMClientBase):
    def __init__(self):
        super().__init__()
        self.project_id = config.llm.gcp.project_id
        self.location = config.llm.gcp.location
        self.model_name = config.llm.gemini_model

        # Set up authentication using service account
        if getattr(sys, "frozen", False):
            # Running as PyInstaller executable
            base_dir = sys._MEIPASS
            service_account_path = os.path.join(
                base_dir, "certs", "hyra-720a2-07066fb5695a.json"
            )
        else:
            # Running from source
            base_dir = os.path.dirname(os.path.abspath(__file__))
            service_account_path = os.path.normpath(
                os.path.join(base_dir, "../../../certs/hyra-720a2-07066fb5695a.json")
            )
        if os.path.exists(service_account_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
            logger.debug(f"Using service account file: {service_account_path}")
        else:
            logger.warning(f"Service account file not found at: {service_account_path}")
            logger.warning("Gemini client may fail without proper authentication")

        # Configure the Gemini client with Vertex AI
        try:
            self.client = genai.Client(
                vertexai=True, project=self.project_id, location=self.location
            )
            logger.debug("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    def call_llm(self, system_prompt: str, user_message: str, return_raw: bool = False) -> Union[List[Dict[str, Any]], str]:
        """Call Gemini with separate system prompt and user message.

        Args:
            system_prompt (str): System prompt
            user_message (str): User message
            return_raw (bool): If True, return raw response text. If False, return parsed XML.

        Returns:
            Union[List[Dict[str, Any]], str]: Parsed XML elements or raw response text
        """
        try:
            # Gemini doesn't have explicit system prompts, so combine them
            combined_prompt = f"{system_prompt}\n\n{user_message}"
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[combined_prompt],
                config={
                    "response_mime_type": "application/json",
                },
            )

            if response.text:
                raw_response = response.text

                # Return raw response or parse XML based on return_raw parameter
                if return_raw:
                    return raw_response
                else:
                    return self.parse_xml_response(raw_response)

            raise Exception("Unexpected response format from Gemini API")

        except Exception as e:
            logger.error(f"Gemini LLM call with system prompt failed: {e}")
            raise
