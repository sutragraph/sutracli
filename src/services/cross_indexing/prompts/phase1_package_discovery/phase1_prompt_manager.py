"""
Package Discovery Prompt Manager

Orchestrates all prompt components for package discovery analysis.
"""

from .cross_index_identity import PHASE1_CROSS_INDEX_IDENTITY
from ..tools.tools import TOOLS_CROSS_INDEXING
from .objective import PACKAGE_DISCOVERY_OBJECTIVE
from .capabilities import PACKAGE_DISCOVERY_CAPABILITIES
from .rules import PACKAGE_DISCOVERY_RULES
from .tool_usage_examples import PACKAGE_DISCOVERY_TOOL_USAGE_EXAMPLES
from .tool_guidelines import PACKAGE_DISCOVERY_TOOL_GUIDELINES
from .sutra_memory import PACKAGE_DISCOVERY_SUTRA_MEMORY
from services.agent.xml_service.xml_service import XMLService
from services.llm_clients.llm_factory import llm_client_factory

class Phase1PromptManager:
    """
    Prompt manager for package discovery analysis.
    
    Orchestrates all prompt components for the first phase of cross-indexing analysis:
    - Identity and base prompts
    - Package discovery guidelines and rules
    - Tool integration and usage
    - Memory context integration
    - Analysis task management
    """

    def __init__(self):
        pass

    def get_system_prompt(self) -> str:
        """
        Get the complete system prompt for package discovery analysis.
        
        Returns:
            Complete system prompt string
        """
        return f"""{PHASE1_CROSS_INDEX_IDENTITY}

{TOOLS_CROSS_INDEXING}

{PACKAGE_DISCOVERY_TOOL_GUIDELINES}

{PACKAGE_DISCOVERY_TOOL_USAGE_EXAMPLES}

{PACKAGE_DISCOVERY_SUTRA_MEMORY}

{PACKAGE_DISCOVERY_OBJECTIVE}

{PACKAGE_DISCOVERY_CAPABILITIES}

{PACKAGE_DISCOVERY_RULES}
"""

    def get_user_prompt(self, analysis_query: str, memory_context: str = "") -> str:
        """
        Get the user prompt for package discovery analysis.
        
        Args:
            analysis_query: The analysis query/request
            memory_context: Current memory context from sutra memory
            
        Returns:
            User prompt string
        """
        user_prompt = f"""ANALYSIS REQUEST: {analysis_query}

SUTRA MEMORY CONTEXT:

{memory_context if memory_context else "No previous context"}
"""

        return user_prompt

    def validate_completion_response(self, response: str) -> bool:
        """
        Validate that the response contains proper attempt_completion XML tag with result.

        Args:
            response: LLM response to validate

        Returns:
            True if response contains valid attempt_completion XML with result, False otherwise
        """
        try:
            xml_service = XMLService(llm_client_factory())
            xml_blocks = xml_service.parse_xml_response(response)

            # Check if any XML block contains attempt_completion with result
            for block in xml_blocks:
                if isinstance(block, dict) and "attempt_completion" in block:
                    attempt_completion = block["attempt_completion"]
                    if isinstance(attempt_completion, dict) and "result" in attempt_completion:
                        result = attempt_completion["result"]
                        if result and str(result).strip():
                            return True

            return False
        except Exception:
            # Fallback to simple string check if XML parsing fails
            return "attempt_completion" in response.lower() and "result" in response.lower()
