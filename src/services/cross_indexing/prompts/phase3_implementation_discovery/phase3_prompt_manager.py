"""
Implementation Discovery Prompt Manager

Orchestrates all prompt components for implementation discovery analysis.
"""

from .cross_index_identity import PHASE3_CROSS_INDEX_IDENTITY
from ..tools.tools import TOOLS_CROSS_INDEXING
from .objective import IMPLEMENTATION_DISCOVERY_OBJECTIVE
from .capabilities import IMPLEMENTATION_DISCOVERY_CAPABILITIES
from .rules import IMPLEMENTATION_DISCOVERY_RULES
from .tool_usage_examples import IMPLEMENTATION_DISCOVERY_TOOL_USAGE_EXAMPLES
from .tool_guidelines import IMPLEMENTATION_DISCOVERY_TOOL_GUIDELINES
from .sutra_memory import IMPLEMENTATION_DISCOVERY_SUTRA_MEMORY

class Phase3PromptManager:
    """
    Prompt manager for implementation discovery analysis.
    
    Orchestrates all prompt components for the third phase of cross-indexing analysis:
    - Identity and base prompts
    - Implementation discovery guidelines and rules
    - Tool integration and usage
    - Memory context integration
    - Analysis task management

    - Additional task creation within phase
    """

    def __init__(self):
        pass

    def get_system_prompt(self) -> str:
        """
        Get the complete system prompt for implementation discovery analysis.
        
        Returns:
            Complete system prompt string
        """
        return f"""{PHASE3_CROSS_INDEX_IDENTITY}

{TOOLS_CROSS_INDEXING}

{IMPLEMENTATION_DISCOVERY_SUTRA_MEMORY}

{IMPLEMENTATION_DISCOVERY_TOOL_GUIDELINES}

{IMPLEMENTATION_DISCOVERY_TOOL_USAGE_EXAMPLES}

{IMPLEMENTATION_DISCOVERY_OBJECTIVE}

{IMPLEMENTATION_DISCOVERY_CAPABILITIES}

{IMPLEMENTATION_DISCOVERY_RULES}
"""

    def get_user_prompt(self, analysis_query: str, memory_context: str = "") -> str:
        """
        Get the user prompt for implementation discovery analysis.
        
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
            from services.agent.xml_service.xml_service import XMLService
            from services.llm_clients.llm_factory import llm_client_factory

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
