"""
Cross-Index Prompt Manager

Main orchestrator for all cross-indexing prompts, guidelines, and tool integration.
"""
from .system.cross_index_identity import CROSS_INDEX_IDENTITY
from .guidelines.cross_index_objective import CROSS_INDEX_OBJECTIVE
from .guidelines.cross_index_capabilities import CROSS_INDEX_CAPABILITIES
from .guidelines.cross_index_rules import CROSS_INDEX_RULES
from .tools.tools import TOOLS_CROSS_INDEXING
from .guidelines.cross_index_tool_guidelines import CROSS_INDEX_TOOL_GUIDELINES
from .guidelines.tool_usage_examples import TOOL_USAGE_EXAMPLES
from .guidelines.sutra_memory import SUTRA_MEMORY
from .connection_matching_manager import ConnectionMatchingManager

class CrossIndexPromptManager:
    """
    Main prompt manager for cross-indexing analysis and connection matching.

    Orchestrates all prompt components:
    - Identity and base prompts
    - Analysis guidelines and rules
    - Tool integration and usage
    - Memory context integration
    - Phase-specific instructions
    - Connection matching workflow
    """

    def __init__(self):
        self.connection_matching_manager = ConnectionMatchingManager()

    def cross_index_system_prompt(self) -> str:
        """
        Get the system prompt for cross-index analysis (without user-specific data).
        
        Args:
            memory_context: Current cross-index memory context
            
        Returns:
            System prompt for cross-index analysis
        """
        return f"""{CROSS_INDEX_IDENTITY}
{TOOLS_CROSS_INDEXING}
{CROSS_INDEX_TOOL_GUIDELINES}
{TOOL_USAGE_EXAMPLES}
{SUTRA_MEMORY}
{CROSS_INDEX_RULES}
{CROSS_INDEX_CAPABILITIES}
{CROSS_INDEX_OBJECTIVE}
"""

    def get_connection_matching_prompt(
        self, incoming_connections, outgoing_connections
    ):
        """
        Get the connection matching prompt for post-analysis matching.

        This method is called after cross-indexing analysis is complete to match
        incoming and outgoing connections and generate JSON response for database storage.

        Args:
            incoming_connections (list): List of incoming connection objects
            outgoing_connections (list): List of outgoing connection objects

        Returns:
            str: Complete connection matching prompt
        """
        return self.connection_matching_manager.build_matching_prompt(
            incoming_connections, outgoing_connections
        )

    def validate_and_process_matching_results(
        self, response_json, incoming_connections, outgoing_connections
    ):
        """
        Validate and process connection matching results.

        Args:
            response_json (dict): JSON response from LLM
            incoming_connections (list): Original incoming connections
            outgoing_connections (list): Original outgoing connections

        Returns:
            tuple: (is_valid, processed_results_or_error)
        """
        # Validate response format
        is_valid, error = self.connection_matching_manager.validate_matching_response(
            response_json
        )
        if not is_valid:
            return False, error

        # Process and enrich results
        processed_results = self.connection_matching_manager.process_matching_results(
            response_json, incoming_connections, outgoing_connections
        )

        return True, processed_results
