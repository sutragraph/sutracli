from typing import Dict, List, Any, Union, NamedTuple, Optional
from services.agent.xml_service import XMLService


class TokenUsage(NamedTuple):
    """Token usage information from LLM calls."""
    input_tokens: int
    output_tokens: int
    total_tokens: int


class LLMResponse(NamedTuple):
    """Response from LLM call including content and token usage."""
    content: Union[List[Dict[str, Any]], str]
    token_usage: Optional[TokenUsage]


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

    def call_llm(self, *args, return_raw: bool = False, **kwargs) -> Union[List[Dict[str, Any]], str]:
        """
        Base method to be implemented by subclasses.
        Subclasses should call parse_xml_response before returning data unless return_raw=True.

        Args:
            return_raw (bool): If True, return raw LLM response text without XML parsing.
                              If False (default), parse and return XML elements.

        Returns:
            Union[List[Dict[str, Any]], str]: List of parsed XML elements if return_raw=False,
                                            raw response text if return_raw=True
        """
        raise NotImplementedError("Subclasses must implement call_llm method")

    def call_llm_with_usage(self, *args, return_raw: bool = False, **kwargs) -> LLMResponse:
        """
        Call LLM and return both content and token usage information.
        Default implementation falls back to call_llm with no token tracking.

        Args:
            return_raw (bool): If True, return raw LLM response text without XML parsing.
                              If False (default), parse and return XML elements.

        Returns:
            LLMResponse: Response containing both content and token usage information
        """
        try:
            content = self.call_llm(*args, return_raw=return_raw, **kwargs)
            return LLMResponse(content=content, token_usage=None)
        except NotImplementedError:
            raise NotImplementedError("Subclasses must implement either call_llm or call_llm_with_usage method")
