"""
Data Splitting Prompt Manager

Orchestrates all prompt components for data splitting in the cross-indexing system.
"""

from .connection_splitting_prompt import CONNECTION_SPLITTING_PROMPT

class Phase4PromptManager:
    """
    Prompt manager for data splitting analysis.

    Orchestrates all prompt components for data splitting in the cross-indexing system:
    - Data splitting objectives and success criteria
    - Processing capabilities and expertise
    - Rules and constraints for accurate data transformation
    - Tool guidelines for data processing workflow
    - Examples of input processing and expected output format
    """

    def __init__(self):
        pass

    def get_system_prompt(self) -> str:
        """
        Get the complete system prompt for data splitting analysis.

        Returns:
            Complete system prompt string for data splitting
        """
        return CONNECTION_SPLITTING_PROMPT

    def get_user_prompt(self, memory_context: str) -> str:
        """
        Get the user prompt for data splitting analysis.

        Args:
            memory_context: Code snippets collected by the code manager from Phase 3

        Returns:
            User prompt string for data splitting processing
        """
        user_prompt = f"""{memory_context}

Process the above connection code snippets and transform them into structured JSON format. Classify each connection as incoming or outgoing, extract complete parameter details, and return the properly formatted JSON for database storage and subsequent connection matching analysis."""

        return user_prompt
