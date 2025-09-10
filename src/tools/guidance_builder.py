"""
Tool Guidance System

Provides guidance and formatting for tool results. Tools with registered guidance
handlers get enhanced with contextual messages, while others pass through unchanged.

Architecture:
- BaseToolGuidance: Abstract base with on_event hook for processing results
- Tool-specific classes: Handle guidance for semantic search, database, and keyword search
- GuidanceRegistry: Factory for retrieving guidance handlers by tool type
"""

from typing import Optional, Dict, Any, List
from abc import ABC
from enum import Enum
from loguru import logger

from models.agent import AgentAction

from tools.utils.constants import (
    GUIDANCE_MESSAGES,
    DATABASE_ERROR_GUIDANCE,
    SEARCH_CONFIG,
)


class SearchType(Enum):
    """Types of search operations."""

    DATABASE = "database"
    SEMANTIC = "semantic"
    KEYWORD = "keyword"


class GuidanceScenario(Enum):
    """Different guidance scenarios for search results."""

    NO_RESULTS_FOUND = "no_results_found"
    SINGLE_RESULT_SMALL = "single_result_small"
    SINGLE_RESULT_LARGE = "single_result_large"
    MULTIPLE_RESULTS = "multiple_results"
    NODE_MISSING_CODE_CONTENT = "node_missing_code_content"
    BATCH_DELIVERY = "batch_delivery"


class SequentialNodeScenario(Enum):
    """Scenarios for sequential node delivery."""

    NODE_WITH_SMALL_CODE = "node_with_small_code"
    NODE_WITH_LARGE_CODE_FIRST_CHUNK = "node_with_large_code_first_chunk"
    NODE_WITH_LARGE_CODE_MIDDLE_CHUNK = "node_with_large_code_middle_chunk"
    NODE_WITH_LARGE_CODE_LAST_CHUNK = "node_with_large_code_last_chunk"
    NODE_NO_CODE_CONTENT = "node_no_code_content"


def _get_fetch_next_chunk_note() -> str:
    """
    Helper function to generate the fetch_next_chunk note.

    Returns:
        Formatted note about fetching next code
    """
    return GUIDANCE_MESSAGES["fetch_next_chunk_NOTE"]


def calculate_database_batch_with_line_limit(
    nodes: List[Dict[str, Any]], line_limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Calculate database batch ensuring total lines don't exceed limit.

    Args:
        nodes: List of node dictionaries with code content
        line_limit: Maximum total lines allowed in batch

    Returns:
        List of nodes that fit within the line limit
    """
    logger.debug(
        f"📦 DEBUG: calculate_database_batch_with_line_limit called with {len(nodes)} nodes, line_limit={line_limit}"
    )

    if not nodes:
        logger.debug("📦 DEBUG: No nodes provided, returning empty batch")
        return []

    batch_nodes = []
    total_lines = 0

    for i, node in enumerate(nodes):
        code_content = node.get("code_snippet", "") or node.get("data", "")
        logger.debug(f"📦 DEBUG: Processing node {i + 1}/{len(nodes)}")
        logger.debug(f"📦 DEBUG: Node keys: {list(node.keys())}")

        if code_content:
            node_lines = len(str(code_content).split("\n"))
            logger.debug(
                f"📦 DEBUG: Node {i + 1} has {node_lines} lines, current total: {total_lines}"
            )

            # Check if adding this node would exceed the limit
            if total_lines + node_lines > line_limit and batch_nodes:
                logger.debug(
                    f"📦 DEBUG: Adding node {
                        i +
                        1} would exceed limit ({
                        total_lines +
                        node_lines} > {line_limit}), stopping batch"
                )
                # Don't add this node, return current batch
                break

            batch_nodes.append(node)
            total_lines += node_lines
            logger.debug(
                f"📦 DEBUG: Added node {i + 1} to batch, new total lines: {total_lines}"
            )
        else:
            logger.debug(f"📦 DEBUG: Node {i + 1} has no code content, adding anyway")
            # Add nodes without code content
            batch_nodes.append(node)

    logger.debug(
        f"📦 DEBUG: Final batch contains {len(batch_nodes)} nodes with {total_lines} total lines"
    )
    return batch_nodes


def build_database_guidance_with_line_info(
    total_nodes: int,
    delivered_nodes: int,
    total_lines: int,
    delivered_lines: int,
    remaining_nodes: int,
    chunk_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build enhanced guidance for database search with line information.

    Args:
        total_nodes: Total number of nodes found
        delivered_nodes: Number of nodes delivered in this batch
        total_lines: Total lines across all nodes
        delivered_lines: Lines delivered in this batch
        remaining_nodes: Number of remaining nodes
        chunk_info: Optional chunk information for line range display

    Returns:
        Formatted guidance message
    """
    if total_nodes == 1:
        # For single node, check chunk info first
        if chunk_info:
            start_line = chunk_info.get("start_line", 1)
            end_line = chunk_info.get("end_line", delivered_lines)
            chunk_num = chunk_info.get("chunk_num", 1)
            total_chunks = chunk_info.get("total_chunks", 1)
            original_file_lines = chunk_info.get("original_file_lines", total_lines)

            if chunk_num < total_chunks:
                message = f"Found 1 node with {original_file_lines} total lines. There are more results available showing only ({start_line}-{end_line} lines)"
                message += _get_fetch_next_chunk_note()
            else:
                message = f"Found 1 node with {original_file_lines} total lines. Showing ({start_line}-{end_line} lines) - This is the final chunk."
        else:
            if delivered_lines < total_lines:
                message = f"Found 1 node with {total_lines} total lines. There are more results available showing only (1-{delivered_lines} lines)"
                message += _get_fetch_next_chunk_note()
            else:
                message = f"Found 1 node with {total_lines} total lines. Showing (1-{delivered_lines} lines) - Complete result."
    else:
        # For multiple nodes, check if we have chunk info to show line ranges
        if chunk_info:
            start_line = chunk_info.get("start_line", 1)
            end_line = chunk_info.get("end_line", delivered_lines)
            chunk_num = chunk_info.get("chunk_num", 1)
            total_chunks = chunk_info.get("total_chunks", 1)
            original_file_lines = chunk_info.get("original_file_lines", total_lines)

            # Show actual line range instead of just counts
            if chunk_num < total_chunks:
                message = f"Found {total_nodes} nodes with {original_file_lines} total lines. There are more results available showing only ({start_line}-{end_line} lines)"
                message += _get_fetch_next_chunk_note()
            else:
                message = f"Found {total_nodes} nodes with {original_file_lines} total lines. Showing ({start_line}-{end_line} lines) - This is the final chunk."
        else:
            # Fallback to original format when no chunk info available
            message = f"Found {total_nodes} nodes with {total_lines} total lines. Delivered {delivered_nodes} nodes ({delivered_lines} lines)."
            if remaining_nodes > 0:
                message += _get_fetch_next_chunk_note()

    return message


def should_chunk_delivery(
    node_data: str, chunk_threshold: Optional[int] = None
) -> bool:
    """
    Determine if node data should be chunked for delivery.

    Args:
        node_data: The data content to check
        chunk_threshold: Custom threshold, uses SEARCH_CONFIG if None

    Returns:
        True if content should be chunked
    """
    if not node_data:
        return False

    threshold = chunk_threshold or SEARCH_CONFIG["chunking_threshold"]
    lines = len(str(node_data).split("\n"))
    return lines > threshold


def enhance_semantic_search_event(
    event: Dict[str, Any], action_parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enhance semantic search event with dynamic guidance.

    Args:
        event: The original event from semantic search
        action: The AgentAction being executed

    Returns:
        Enhanced event with guidance
    """
    if not event.get("batch_info"):
        return event

    batch_info = event["batch_info"]
    total_nodes = event.get("total_nodes", 0)
    delivered_count = batch_info.get("delivered_count", 0)
    remaining_count = batch_info.get("remaining_count", 0)

    # Calculate line information from data
    data = event.get("data", "")
    current_lines = len(str(data).split("\n")) if data else 0

    # Build enhanced guidance
    start_node = max(1, delivered_count - batch_info.get("batch_size", 15) + 1)
    end_node = delivered_count

    guidance_message = f"Showing nodes {start_node} to {end_node} of {total_nodes}"

    if remaining_count > 0:
        guidance_message += f"""\nNOTE: There are more results available. Use `"fetch_next_chunk" : true`  to get next codes for your current query. ({remaining_count} more nodes available)"""
    else:
        guidance_message += "."

    # Add guidance as prefix to data
    event = GuidanceFormatter.add_prefix_to_data(event, guidance_message)
    return event


def enhance_database_search_event(
    event: Dict[str, Any],
    action_parameters: Dict[str, Any],
    delivery_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enhance database search event with dynamic guidance based on line counting.

    Args:
        event: The original event from database search
        action_parameters: The AgentAction being executed
        delivery_context: Optional context about delivery state

    Returns:
        Enhanced event with guidance
    """
    total_nodes = event.get("total_nodes", 0)
    data = event.get("data", "")

    if total_nodes == 0 or not data:
        return event

    # Check if this is a metadata-only query (like GET_FILE_BLOCK_SUMMARY)
    query_name = action_parameters.get("query_name", "")
    include_code = event.get("code_snippet", True)
    is_metadata_only = query_name == "GET_FILE_BLOCK_SUMMARY" or not include_code

    # For metadata-only queries, just show node count without line information
    if is_metadata_only:
        if total_nodes == 1:
            guidance_message = f"Found 1 node."
        else:
            remaining_nodes = (
                delivery_context.get("remaining_nodes", 0) if delivery_context else 0
            )
            guidance_message = f"Found {total_nodes} nodes."
            if remaining_nodes > 0:
                guidance_message += _get_fetch_next_chunk_note()

        # Add guidance as prefix to data
        event = GuidanceFormatter.add_prefix_to_data(event, guidance_message)
        return event

    # Use delivery context line info if available, otherwise calculate
    if delivery_context and "delivered_lines" in delivery_context:
        current_lines = delivery_context["delivered_lines"]
        total_lines = delivery_context.get("total_lines", current_lines)
    else:
        current_lines = len(str(data).split("\n"))
        total_lines = current_lines

    # Get delivery context information
    remaining_nodes = (
        delivery_context.get("remaining_nodes", 0) if delivery_context else 0
    )
    delivered_nodes = (
        delivery_context.get("delivered_nodes", 1) if delivery_context else 1
    )

    # Check for chunk info in the event itself (for chunked content)
    chunk_info = event.get("chunk_info")
    if not chunk_info and delivery_context:
        chunk_info = delivery_context.get("chunk_info")

    # Handle chunked content
    if chunk_info:
        start_line = chunk_info.get("start_line", 1)
        end_line = chunk_info.get("end_line", 0)
        chunk_num = chunk_info.get("chunk_num", 1)
        total_chunks = chunk_info.get("total_chunks", 1)
        original_file_lines = chunk_info.get("original_file_lines", 0)

        # Check if there are more chunks to determine the message
        if chunk_num < total_chunks:
            guidance_message = f"Found 1 node with {original_file_lines} total lines. There are more results available showing only ({start_line}-{end_line} lines)"
            guidance_message += f"""\n\nNOTE: There are more chunks available. Use `"fetch_next_chunk" : true` to get the next chunk ({total_chunks - chunk_num} more chunks remaining).

Chunk {chunk_num}/{total_chunks}: (Showing Chunk no {chunk_num} Remaining {total_chunks - chunk_num} chunks)"""
        else:
            guidance_message = f"Found 1 node with {original_file_lines} total lines. Showing ({start_line}-{end_line} lines) - This is the final chunk."

        # Add guidance as prefix to data
        event = GuidanceFormatter.add_prefix_to_data(event, guidance_message)
        return event

    if total_nodes == 1:
        # Single node scenario (non-chunked)
        if should_chunk_delivery(data):
            # Fallback to content-based chunking detection
            if current_lines < total_lines:
                guidance_message = f"Found 1 node with {total_lines} total lines. There are more results available showing only (1-{current_lines} lines)"
                guidance_message += _get_fetch_next_chunk_note()
            else:
                guidance_message = f"Found 1 node with {total_lines} total lines. Showing (1-{current_lines} lines) - Complete result."
        else:
            guidance_message = f"Found 1 node with {current_lines} lines (complete)."
    else:
        # Multiple nodes scenario - use enhanced guidance with actual line info
        guidance_message = build_database_guidance_with_line_info(
            total_nodes=total_nodes,
            delivered_nodes=delivered_nodes,
            total_lines=total_lines,
            delivered_lines=current_lines,
            remaining_nodes=remaining_nodes,
            chunk_info=None,  # Multiple nodes don't use chunk_info
        )

    # Add guidance as prefix to data
    event = GuidanceFormatter.add_prefix_to_data(event, guidance_message)
    return event


class BaseToolGuidance(ABC):
    """
    Base class for tool guidance handlers.

    Provides a single hook for processing tool events:
    - on_event: Called for each event yielded by the tool to add contextual guidance
    """

    def on_event(self, event: Dict[str, Any], action: AgentAction) -> Dict[str, Any]:
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

        new_data = f"{prefix}\n\n{data}".strip() if data else prefix
        event["data"] = new_data

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
    - Provide dynamic guidance for batch delivery with node and line information
    """

    def on_event(self, event: Dict[str, Any], action: AgentAction) -> Dict[str, Any]:
        # Validate event data
        if not self._validate_event(event):
            logger.warning(f"Invalid event data for semantic search guidance: {event}")
            return event

        # Only process semantic search events
        if not self._is_semantic_search_event(event):
            return event

        # Handle no results case
        if self._has_no_results(event):
            message = GuidanceFormatter.format_no_results_message("semantic")
            return GuidanceFormatter.add_prefix_to_data(event, message)

        # Handle multiple results with batch info
        if self._has_batch_info(event):
            guidance_message = self._build_semantic_batch_guidance(event)
            if guidance_message:
                return GuidanceFormatter.add_prefix_to_data(event, guidance_message)

        return event

    def _validate_event(self, event: Dict[str, Any]) -> bool:
        """Validate that event has required fields."""
        if not isinstance(event, dict):
            return False

        required_fields = ["type", "tool_name"]
        return all(field in event for field in required_fields)

    def _is_semantic_search_event(self, event: Dict[str, Any]) -> bool:
        """Check if this is a semantic search event."""
        return isinstance(event, dict) and event.get("tool_name") == "semantic_search"

    def _has_no_results(self, event: Dict[str, Any]) -> bool:
        """Check if the semantic search returned no results."""
        return event.get("total_nodes") == 0

    def _has_batch_info(self, event: Dict[str, Any]) -> bool:
        """Check if the event contains batch information."""
        return event.get("batch_info") is not None

    def _build_semantic_batch_guidance(self, event: Dict[str, Any]) -> Optional[str]:
        """Build guidance message for semantic search batch delivery."""
        batch_info = event.get("batch_info", {})
        total_nodes = event.get("total_nodes", 0)

        if total_nodes == 0:
            return None

        delivered_count = batch_info.get("delivered_count", 0)
        remaining_count = batch_info.get("remaining_count", 0)

        start_range = max(1, delivered_count - batch_info.get("batch_size", 15) + 1)
        end_range = delivered_count

        message = f"Showing nodes {start_range} to {end_range} of {total_nodes}."

        # Add fetch_next_chunk note if there are remaining nodes, but without line numbers
        if remaining_count > 0:
            message += f"""\nNOTE: There are more results available. Use `"fetch_next_chunk" : true` to get next codes for your current query. ({remaining_count} more nodes available)"""

        return message


class DatabaseSearchGuidance(BaseToolGuidance):
    """
    Guidance handler for database search tool.

    Responsibilities:
    - Generate error guidance for failed queries
    - Handle no results scenarios
    - Provide dynamic guidance for batch delivery with line counting
    """

    def on_event(self, event: Dict[str, Any], action: AgentAction) -> Dict[str, Any]:
        # Validate event data
        if not self._validate_event(event):
            logger.warning(f"Invalid event data for database search guidance: {event}")
            return event

        # Only process database events
        if not self._is_database_event(event):
            return event

        # Handle no results case with enhanced error guidance
        if self._has_no_results(event):
            return self._handle_no_results(event, action)

        # Handle batch delivery with line counting
        if self._should_add_batch_guidance(event):
            guidance_message = self._build_database_batch_guidance(event)
            if guidance_message:
                return GuidanceFormatter.add_prefix_to_data(event, guidance_message)

        return event

    def _validate_event(self, event: Dict[str, Any]) -> bool:
        """Validate that event has required fields."""
        if not isinstance(event, dict):
            return False

        required_fields = ["type", "tool_name"]
        return all(field in event for field in required_fields)

    def _is_database_event(self, event: Dict[str, Any]) -> bool:
        """Check if this is a database event."""
        return isinstance(event, dict) and event.get("tool_name") == "database"

    def _has_no_results(self, event: Dict[str, Any]) -> bool:
        """Check if the database query returned no results."""
        result = event.get("result", "")
        return isinstance(result, str) and result.endswith(": 0")

    def _should_add_batch_guidance(self, event: Dict[str, Any]) -> bool:
        """Check if we should add batch guidance for database results."""
        # Add guidance if there are multiple results or large code content
        total_nodes = event.get("total_nodes", 0)
        has_code_snippet = event.get("code_snippet", False)
        has_chunk_info = event.get("chunk_info") is not None

        # Always add guidance for chunked content or when there are results with code
        return (total_nodes > 0 and has_code_snippet) or has_chunk_info

    def _build_database_batch_guidance(self, event: Dict[str, Any]) -> Optional[str]:
        """Build guidance message for database batch delivery with line counting."""
        data = event.get("data", "")
        total_nodes = event.get("total_nodes", 0)

        if not data or total_nodes == 0:
            return None

        # Calculate line information
        delivered_lines = len(str(data).split("\n")) if data else 0

        # Check if this is chunked content by looking for chunk_info
        chunk_info = event.get("chunk_info")
        is_chunked_content = chunk_info is not None

        # For database queries, we need to estimate or track total lines
        if is_chunked_content:
            # Use actual chunk information for accurate line counting
            estimated_total_lines = chunk_info.get(
                "original_file_lines", delivered_lines
            )
        else:
            estimated_total_lines = (
                delivered_lines * total_nodes if total_nodes > 1 else delivered_lines
            )

        # Check if this is likely a chunked/batched delivery
        result = event.get("result", "")
        is_chunked = (
            is_chunked_content
            or "chunk" in str(result).lower()
            or delivered_lines > SEARCH_CONFIG["chunking_threshold"]
        )

        if is_chunked or total_nodes > 1:
            # Use enhanced database guidance with line info
            remaining_nodes = max(0, total_nodes - 1) if total_nodes > 1 else 0

            return build_database_guidance_with_line_info(
                total_nodes=total_nodes,
                delivered_nodes=1 if total_nodes > 0 else 0,
                total_lines=estimated_total_lines,
                delivered_lines=delivered_lines,
                remaining_nodes=remaining_nodes,
                chunk_info=chunk_info,
            )

        return None

    def _handle_no_results(self, event: Dict[str, Any], action: AgentAction) -> Dict[str, Any]:
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
        excluded_keys = {"query_name", "code_snippet", "fetch_next_chunk"}
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


class ListFilesGuidance(BaseToolGuidance):
    """
    Guidance handler for list_files tool.

    Responsibilities:
    - Handle no results scenarios
    - Provide dynamic guidance for chunked delivery with line counting
    """

    def on_event(self, event: Dict[str, Any], action: AgentAction) -> Dict[str, Any]:
        # Validate event data
        if not self._validate_event(event):
            logger.warning(f"Invalid event data for list_files guidance: {event}")
            return event

        # Only process list_files events
        if not self._is_list_files_event(event):
            return event

        # Handle no results case
        if self._has_no_results(event):
            message = GuidanceFormatter.format_no_results_message("list_files")
            return GuidanceFormatter.add_prefix_to_data(event, message)

        # Handle chunked delivery
        if self._should_add_chunk_guidance(event):
            guidance_message = self._build_chunk_guidance(event)
            if guidance_message:
                return GuidanceFormatter.add_prefix_to_data(event, guidance_message)

        return event

    def _validate_event(self, event: Dict[str, Any]) -> bool:
        """Validate that event has required fields."""
        if not isinstance(event, dict):
            return False

        required_fields = ["type", "tool_name"]
        return all(field in event for field in required_fields)

    def _is_list_files_event(self, event: Dict[str, Any]) -> bool:
        """Check if this is a list_files event."""
        return isinstance(event, dict) and event.get("tool_name") == "list_files"

    def _has_no_results(self, event: Dict[str, Any]) -> bool:
        """Check if the list_files returned no results."""
        count = event.get("count", 0)
        return count == 0

    def _should_add_chunk_guidance(self, event: Dict[str, Any]) -> bool:
        """Check if we should add chunk guidance for list_files results."""
        return event.get("chunk_info") is not None

    def _build_chunk_guidance(self, event: Dict[str, Any]) -> Optional[str]:
        """Build guidance message for list_files chunk delivery."""
        chunk_info = event.get("chunk_info")
        if not chunk_info:
            return None

        chunk_num = chunk_info.get("chunk_num", 1)
        total_chunks = chunk_info.get("total_chunks", 1)
        start_line = chunk_info.get("start_line", 1)
        end_line = chunk_info.get("end_line", 0)
        original_file_lines = chunk_info.get("original_file_lines", 0)

        # Check if there are more chunks to determine the message
        if chunk_num < total_chunks:
            message = f"Found file listing with {original_file_lines} total lines. There are more results available showing only ({start_line}-{end_line} lines)"
            message += f"""\n\nNOTE: There are more chunks available. Use `"fetch_next_chunk" : true` to get the next chunk ({total_chunks - chunk_num} more chunks remaining).

Chunk {chunk_num}/{total_chunks}: (Showing Chunk no {chunk_num} Remaining {total_chunks - chunk_num} chunks)"""
        else:
            message = f"Found file listing with {original_file_lines} total lines. Showing ({start_line}-{end_line} lines) - This is the final chunk."

        return message


class SearchKeywordGuidance(BaseToolGuidance):
    """
    Guidance handler for search_keyword tool.

    Responsibilities:
    - Handle no results scenarios
    - Provide dynamic guidance for chunked delivery with line counting
    """

    def on_event(self, event: Dict[str, Any], action: AgentAction) -> Dict[str, Any]:
        # Validate event data
        if not self._validate_event(event):
            logger.warning(f"Invalid event data for search_keyword guidance: {event}")
            return event

        # Only process search_keyword events
        if not self._is_search_keyword_event(event):
            return event

        # Handle no results case
        if self._has_no_results(event):
            message = GuidanceFormatter.format_no_results_message("keyword search")
            return GuidanceFormatter.add_prefix_to_data(event, message)

        # Handle chunked delivery
        if self._should_add_chunk_guidance(event):
            guidance_message = self._build_chunk_guidance(event)
            if guidance_message:
                return GuidanceFormatter.add_prefix_to_data(event, guidance_message)

        return event

    def _validate_event(self, event: Dict[str, Any]) -> bool:
        """Validate that event has required fields."""
        if not isinstance(event, dict):
            return False

        required_fields = ["type", "tool_name"]
        return all(field in event for field in required_fields)

    def _is_search_keyword_event(self, event: Dict[str, Any]) -> bool:
        """Check if this is a search_keyword event."""
        return isinstance(event, dict) and event.get("tool_name") == "search_keyword"

    def _has_no_results(self, event: Dict[str, Any]) -> bool:
        """Check if the search_keyword returned no results."""
        matches_found = event.get("matches_found", False)
        return not matches_found

    def _should_add_chunk_guidance(self, event: Dict[str, Any]) -> bool:
        """Check if we should add chunk guidance for search_keyword results."""
        return event.get("chunk_info") is not None

    def _build_chunk_guidance(self, event: Dict[str, Any]) -> Optional[str]:
        """Build guidance message for search_keyword chunk delivery."""
        chunk_info = event.get("chunk_info")
        if not chunk_info:
            return None

        chunk_num = chunk_info.get("chunk_num", 1)
        total_chunks = chunk_info.get("total_chunks", 1)
        start_line = chunk_info.get("start_line", 1)
        end_line = chunk_info.get("end_line", 0)
        original_file_lines = chunk_info.get("original_file_lines", 0)

        # Check if there are more chunks to determine the message
        if chunk_num < total_chunks:
            message = f"Found keyword matches with {original_file_lines} total result lines. There are more results available showing only ({start_line}-{end_line} lines)"
            message += f"""\n\nNOTE: There are more chunks available. Use `"fetch_next_chunk" : true` to get the next chunk ({total_chunks - chunk_num} more chunks remaining).

Chunk {chunk_num}/{total_chunks}: (Showing Chunk no {chunk_num} Remaining {total_chunks - chunk_num} chunks)"""
        else:
            message = f"Found keyword matches with {original_file_lines} total result lines. Showing ({start_line}-{end_line} lines) - This is the final chunk."

        return message


class GuidanceRegistry:
    """
    Registry for tool guidance handlers.

    Maps tool types to their guidance classes and provides
    a factory method for creating guidance instances.
    """

    _HANDLERS = {
        "semantic_search": SemanticSearchGuidance,
        "database": DatabaseSearchGuidance,
        "list_files": ListFilesGuidance,
        "search_keyword": SearchKeywordGuidance,
    }

    @classmethod
    def get_guidance(cls, tool_name: str) -> Optional[BaseToolGuidance]:
        """
        Get guidance handler for the specified tool.

        Args:
            tool_name: The tool name to get guidance for

        Returns:
            Guidance handler instance or None if no guidance exists
        """
        guidance_class = cls._HANDLERS.get(tool_name)
        return guidance_class() if guidance_class else None

    @classmethod
    def register_guidance(cls, tool_name: str, guidance_class: type):
        """
        Register a new guidance handler.

        Args:
            tool_name: The tool name
            guidance_class: The guidance class to register
        """
        cls._HANDLERS[tool_name] = guidance_class

    @classmethod
    def get_supported_tools(cls) -> List[str]:
        """Get list of tools that have guidance support."""
        return list(cls._HANDLERS.keys())


# Public factory function for backward compatibility
def get_tool_guidance(tool_name: str) -> Optional[BaseToolGuidance]:
    """
    Factory function to get guidance handler for a tool.

    Args:
        tool_name: The tool name to get guidance for

    Returns:
        Guidance handler instance or None if no guidance exists
    """
    return GuidanceRegistry.get_guidance(tool_name)
