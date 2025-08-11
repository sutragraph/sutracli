"""
Tool Guidance System

Provides guidance and formatting for tool results. Each tool can have optional
guidance hooks that are called by the ActionExecutor during tool execution.

Architecture:
- BaseToolGuidance: Abstract base with hooks for tool lifecycle
- Tool-specific classes: Handle guidance for semantic search, database, and keyword search
- GuidanceRegistry: Factory for retrieving guidance handlers by tool type
"""

from typing import Optional, Dict, Any, List
from abc import ABC

from tools.utils.constants import (
    GUIDANCE_MESSAGES,
    DATABASE_ERROR_GUIDANCE,
)
from tools import ToolName


class BaseToolGuidance(ABC):
    """
    Base class for tool guidance handlers.

    Provides hooks for tool lifecycle events:
    - on_start: Called before tool execution
    - on_event: Called for each event yielded by the tool
    """

    def on_start(self, action) -> Optional[Dict[str, Any]]:
        """
        Pre-execution hook called before tool starts.

        Args:
            action: The AgentAction being executed

        Returns:
            Optional event to yield before tool execution
        """
        return None

    def on_event(self, event: Dict[str, Any], action) -> Optional[Dict[str, Any]]:
        """
        Post-execution hook called for each tool event.

        Args:
            event: Event yielded by the tool
            action: The AgentAction being executed

        Returns:
            Modified event or None to filter out the event
        """
        return event


class GuidanceFormatter:
    """
    Utility class for common guidance formatting operations.
    """

    @staticmethod
    def add_prefix_to_data(event: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """Add a prefix to the event data."""
        data = event.get("data", "")
        event["data"] = f"{prefix}\n\n{data}".strip() if data else prefix
        return event

    @staticmethod
    def has_prefix(data: str, prefixes: List[str]) -> bool:
        """Check if data already has one of the given prefixes."""
        if not data:
            return False
        data_start = data.lstrip()
        return any(data_start.startswith(prefix) for prefix in prefixes)

    @staticmethod
    def format_no_results_message(search_type: str) -> str:
        """Format a no results message for the given search type."""
        template = GUIDANCE_MESSAGES.get(
            "NO_RESULTS_FOUND", "No results found for {search_type} search."
        )
        return template.format(search_type=search_type)


class SemanticSearchGuidance(BaseToolGuidance):
    """
    Guidance handler for semantic search tool.

    Responsibilities:
    - Add helpful messages when no results are found
    """

    def on_event(self, event: Dict[str, Any], action) -> Optional[Dict[str, Any]]:
        # Only process semantic search events
        if not self._is_semantic_search_event(event):
            return event

        # Handle no results case
        if self._has_no_results(event):
            message = GuidanceFormatter.format_no_results_message("semantic")
            return GuidanceFormatter.add_prefix_to_data(event, message)

        return event

    def _is_semantic_search_event(self, event: Dict[str, Any]) -> bool:
        """Check if this is a semantic search event."""
        return isinstance(event, dict) and event.get("tool_name") == "semantic_search"

    def _has_no_results(self, event: Dict[str, Any]) -> bool:
        """Check if the semantic search returned no results."""
        return event.get("total_nodes") == 0


class DatabaseSearchGuidance(BaseToolGuidance):
    """
    Guidance handler for database search tool.

    Responsibilities:
    - Generate error guidance for failed queries
    - Handle no results scenarios
    """

    def on_event(self, event: Dict[str, Any], action) -> Optional[Dict[str, Any]]:
        # Only process database events
        if not self._is_database_event(event):
            return event

        # Handle no results case with enhanced error guidance
        if self._has_no_results(event):
            return self._handle_no_results(event, action)

        return event

    def _is_database_event(self, event: Dict[str, Any]) -> bool:
        """Check if this is a database event."""
        return isinstance(event, dict) and event.get("tool_name") == "database"

    def _has_no_results(self, event: Dict[str, Any]) -> bool:
        """Check if the database query returned no results."""
        result = event.get("result", "")
        return isinstance(result, str) and result.endswith(": 0")

    def _handle_no_results(self, event: Dict[str, Any], action) -> Dict[str, Any]:
        """Handle no results case with comprehensive error guidance."""
        # Build error guidance
        query_name = action.parameters.get("query_name", "unknown")
        query_params = self._extract_query_params(action.parameters)

        no_results_msg = GuidanceFormatter.format_no_results_message("database")
        error_guidance = self._generate_error_guidance(query_name, query_params)

        # Combine messages
        combined_guidance = f"{no_results_msg}\n\n{error_guidance}"
        return GuidanceFormatter.add_prefix_to_data(event, combined_guidance)

    def _extract_query_params(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant query parameters excluding internal ones."""
        excluded_keys = {"query_name", "code_snippet", "fetch_next_code"}
        return {k: v for k, v in parameters.items() if k not in excluded_keys}

    def _generate_error_guidance(self, query_name: str, params: Dict[str, Any]) -> str:
        """Build comprehensive error guidance for failed queries."""
        guidance_parts = []

        # Parameter-specific guidance
        if "file_path" in params:
            guidance_parts.append(
                f"Ensure file_path '{params['file_path']}' is case-sensitive and complete. "
                "If unsure, use semantic_search to find the correct path."
            )

        if "function_name" in params:
            guidance_parts.append(
                f"Ensure function_name '{params['function_name']}' is spelled correctly. "
                "Try semantic_search for similar function names."
            )

        if "name" in params:
            guidance_parts.append(
                f"Ensure name '{params['name']}' exists in the codebase. "
                "Try semantic_search for partial matches."
            )

        # Query-specific guidance from constants
        if query_name in DATABASE_ERROR_GUIDANCE:
            guidance_parts.append(DATABASE_ERROR_GUIDANCE[query_name])

        # General guidance
        guidance_parts.append(
            "Do not reuse these exact parameters. Try different search methods or terms."
        )

        return " ".join(guidance_parts)


class GuidanceRegistry:
    """
    Registry for tool guidance handlers.

    Maps tool types to their guidance classes and provides
    a factory method for creating guidance instances.
    """

    _HANDLERS = {
        ToolName.SEMANTIC_SEARCH: SemanticSearchGuidance,
        ToolName.DATABASE_SEARCH: DatabaseSearchGuidance,
    }

    @classmethod
    def get_guidance(cls, tool_enum: ToolName) -> Optional[BaseToolGuidance]:
        """
        Get guidance handler for the specified tool.

        Args:
            tool_enum: The tool type to get guidance for

        Returns:
            Guidance handler instance or None if no guidance exists
        """
        guidance_class = cls._HANDLERS.get(tool_enum)
        return guidance_class() if guidance_class else None

    @classmethod
    def register_guidance(cls, tool_enum: ToolName, guidance_class: type):
        """
        Register a new guidance handler.

        Args:
            tool_enum: The tool type
            guidance_class: The guidance class to register
        """
        cls._HANDLERS[tool_enum] = guidance_class

    @classmethod
    def get_supported_tools(cls) -> List[ToolName]:
        """Get list of tools that have guidance support."""
        return list(cls._HANDLERS.keys())


# Public factory function for backward compatibility
def get_tool_guidance(tool_enum: ToolName) -> Optional[BaseToolGuidance]:
    """
    Factory function to get guidance handler for a tool.

    Args:
        tool_enum: The tool type to get guidance for

    Returns:
        Guidance handler instance or None if no guidance exists
    """
    return GuidanceRegistry.get_guidance(tool_enum)
