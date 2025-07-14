from typing import Dict, List, Any
from ..agent.xml_service import XMLService


class LLMClientBase:
    """Base class for all LLM clients with XML processing capabilities."""

    def __init__(self):
        self.xml_service = XMLService(self)

    def parse_xml_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response and extract only XML data.
        Delegates to XMLService for all XML processing operations.

        Args:
            response_text (str): Raw LLM response text

        Returns:
            List[Dict[str, Any]]: List of parsed XML elements only
        """
        return self.xml_service.parse_xml_response(response_text)

    def call_llm(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Base method to be implemented by subclasses.
        Subclasses should call parse_xml_response before returning data.

        Returns:
            List of parsed XML elements
        """
        raise NotImplementedError("Subclasses must implement call_llm method")
