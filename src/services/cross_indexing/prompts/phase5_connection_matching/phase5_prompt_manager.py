"""
Connection Matching Prompt Manager

Orchestrates all prompt components for connection matching analysis.
"""

from ...core.connection_matching_manager import ConnectionMatchingManager
from .connection_matching_prompt import CONNECTION_MATCHING_PROMPT

class Phase5PromptManager(ConnectionMatchingManager):
    """
    Prompt manager for connection matching analysis.

    Inherits from ConnectionMatchingManager to provide all connection matching functionality
    including database operations, prompt building, and result validation.
    """

    def __init__(self):
        super().__init__()

    def get_system_prompt(self) -> str:
        """
        Get the complete system prompt for connection matching analysis.

        Returns:
            Complete system prompt string
        """
        return CONNECTION_MATCHING_PROMPT
