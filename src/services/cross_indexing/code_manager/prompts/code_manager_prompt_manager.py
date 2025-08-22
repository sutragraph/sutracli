"""
Code Manager Prompt Manager

Main orchestrator for all code manager prompts and guidelines.
"""

from .guidelines.code_manager_objective import CODE_MANAGER_OBJECTIVE
from .guidelines.code_manager_capabilities import CODE_MANAGER_CAPABILITIES
from .guidelines.code_manager_rules import CODE_MANAGER_RULES
from .guidelines.code_manager_output_format import CODE_MANAGER_OUTPUT_FORMAT
from .guidelines.code_manager_examples import CODE_MANAGER_EXAMPLES


class CodeManagerPromptManager:
    """
    Main orchestrator for all code manager prompts, guidelines, and tool integration.
    """

    def __init__(self):
        self.objective = CODE_MANAGER_OBJECTIVE
        self.capabilities = CODE_MANAGER_CAPABILITIES
        self.rules = CODE_MANAGER_RULES
        self.output_format = CODE_MANAGER_OUTPUT_FORMAT
        self.examples = CODE_MANAGER_EXAMPLES

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the code manager (cacheable).

        Returns:
            System prompt string containing static guidelines and rules
        """
        prompt_parts = [
            "You are a Code Manager responsible for extracting connection code from cross-indexing analysis results.",
            "",
            "Your role is to:",
            "1. Extract connection code",
            "2. Extract environment variables are important for connection code (for resolving endpoints, queue names, etc.)",
            "3. Return XML format with extracted connection code",
            "4. Return nothing if no connection code is found",
            "",
            self.objective,
            "",
            self.capabilities,
            "",
            self.rules,
            "",
            self.output_format,
            "",
            self.examples,
        ]

        return "\n".join(prompt_parts)

    def get_user_prompt(self, tool_results: str) -> str:
        """
        Get the user prompt containing tool results (non-cacheable).

        Args:
            tool_results: Raw tool results from cross-indexing analysis

        Returns:
            User prompt string containing tool results to analyze
        """
        prompt_parts = [
            "# TOOL RESULTS TO ANALYZE",
            "",
            "Please analyze the following tool results from cross-indexing analysis and extract any connection code that should be returned:",
            "",
            "```",
            tool_results,
            "```",
        ]

        return "\n".join(prompt_parts)

    def build_extraction_prompt(self, tool_results: str) -> str:
        """
        Build the complete code manager prompt for extracting connection code.
        
        DEPRECATED: Use get_system_prompt() and get_user_prompt() separately for better caching.

        Args:
            tool_results: Raw tool results from cross-indexing analysis

        Returns:
            Complete prompt for the code manager
        """
        system_prompt = self.get_system_prompt()
        user_prompt = self.get_user_prompt(tool_results)

        return f"{system_prompt}\n\n{user_prompt}"
