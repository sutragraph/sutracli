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
from enum import Enum
from loguru import logger

from tools.utils.constants import (
    GUIDANCE_MESSAGES,
    DATABASE_ERROR_GUIDANCE,
    SEARCH_CONFIG,
)
from tools import ToolName


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


def _get_fetch_next_code_note() -> str:
    """
    Helper function to generate the fetch_next_code note.

    Returns:
        Formatted note about fetching next code
    """
    return GUIDANCE_MESSAGES["FETCH_NEXT_CODE_NOTE"]


def build_guidance_message(
    search_type: SearchType, scenario: GuidanceScenario, **kwargs
) -> str:
    """
    Build guidance message based on search type and scenario.

    Args:
        search_type: Type of search operation
        scenario: Guidance scenario
        **kwargs: Additional parameters for message building

    Returns:
        Formatted guidance message
    """
    if scenario == GuidanceScenario.NO_RESULTS_FOUND:
        return GUIDANCE_MESSAGES["NO_RESULTS_FOUND"].format(
            search_type=search_type.value
        )

    elif scenario == GuidanceScenario.SINGLE_RESULT_SMALL:
        return f"Found 1 result from {search_type.value} search."

    elif scenario == GuidanceScenario.SINGLE_RESULT_LARGE:
        has_more_chunks = kwargs.get("has_more_chunks", False)
        chunk_num = kwargs.get("chunk_num", 1)
        total_chunks = kwargs.get("total_chunks", 1)
        message = f"Found 1 result from {search_type.value} search."
        if has_more_chunks or chunk_num < total_chunks:
            message += _get_fetch_next_code_note()
        return message

    elif scenario == GuidanceScenario.MULTIPLE_RESULTS:
        total_nodes = kwargs.get("total_nodes", 0)
        has_more_results = kwargs.get("has_more_results", False)
        current_node = kwargs.get("current_node", 1)
        delivered_count = kwargs.get("delivered_count", 0)
        remaining_count = kwargs.get("remaining_count", 0)

        if search_type == SearchType.SEMANTIC:
            # Enhanced guidance for semantic search
            start_range = (
                (delivered_count - len(range(delivered_count))) + 1
                if delivered_count > 0
                else 1
            )
            end_range = delivered_count if delivered_count > 0 else total_nodes
            message = f"Found {total_nodes} nodes from {search_type.value} search. Showing nodes {start_range} to {end_range}."
            if remaining_count > 0:
                message += _get_fetch_next_code_note()
        else:
            # Original logic for other search types
            message = f"Found {total_nodes} results from {search_type.value} search"
            if has_more_results or current_node < total_nodes:
                message += _get_fetch_next_code_note()
        return message

    elif scenario == GuidanceScenario.NODE_MISSING_CODE_CONTENT:
        return GUIDANCE_MESSAGES["NODE_MISSING_CODE"]

    elif scenario == GuidanceScenario.BATCH_DELIVERY:
        remaining_count = kwargs.get("remaining_count", 0)
        total_nodes = kwargs.get("total_nodes", 0)
        message = ""
        if remaining_count > 0:
            message = _get_fetch_next_code_note()
        return message

    return f"Results from {search_type.value} search."


def determine_guidance_scenario(
    total_nodes: int,
    include_code: bool,
    code_lines: Optional[int] = None,
    chunk_info: Optional[Dict[str, Any]] = None,
    **kwargs,  # Accept additional parameters for flexibility
) -> GuidanceScenario:
    """
    Determine the appropriate guidance scenario based on search results.

    Args:
        total_nodes: Total number of nodes found
        include_code: Whether code snippets are included
        code_lines: Number of lines in code (if applicable)
        chunk_info: Information about chunking (if applicable)
        **kwargs: Additional parameters for flexibility

    Returns:
        Appropriate guidance scenario
    """
    if total_nodes == 0:
        return GuidanceScenario.NO_RESULTS_FOUND

    elif total_nodes == 1:
        if not include_code or not code_lines:
            return GuidanceScenario.NODE_MISSING_CODE_CONTENT
        elif code_lines > SEARCH_CONFIG["chunking_threshold"]:
            return GuidanceScenario.SINGLE_RESULT_LARGE
        else:
            return GuidanceScenario.SINGLE_RESULT_SMALL

    else:
        return GuidanceScenario.MULTIPLE_RESULTS


def determine_sequential_node_scenario(
    chunk_info: Optional[Dict[str, Any]] = None,
) -> SequentialNodeScenario:
    """
    Determine the sequential node scenario for guidance.

    Args:
        chunk_info: Information about chunking

    Returns:
        Appropriate sequential node scenario
    """
    if not chunk_info:
        return SequentialNodeScenario.NODE_WITH_SMALL_CODE

    # Handle chunked scenarios
    chunk_num = chunk_info.get("chunk_num", 1)
    total_chunks = chunk_info.get("total_chunks", 1)

    if chunk_num == 1:
        return SequentialNodeScenario.NODE_WITH_LARGE_CODE_FIRST_CHUNK
    elif chunk_num == total_chunks:
        return SequentialNodeScenario.NODE_WITH_LARGE_CODE_LAST_CHUNK
    else:
        return SequentialNodeScenario.NODE_WITH_LARGE_CODE_MIDDLE_CHUNK


def determine_semantic_batch_scenario() -> GuidanceScenario:
    """
    Determine guidance scenario for semantic search batch delivery.

    Returns:
        Appropriate guidance scenario
    """
    return GuidanceScenario.BATCH_DELIVERY


def analyze_result_set_for_large_files(results: List[Dict[str, Any]]) -> bool:
    """
    Analyze search results to determine if any files contain large code content.

    Args:
        results: List of search result dictionaries

    Returns:
        bool: True if any files are considered large, False otherwise
    """
    if not results:
        return False

    # Check each result for large code content
    for result in results:
        code_snippet = result.get("code_snippet", "")
        if code_snippet:
            # Consider a file large if it exceeds chunking threshold
            line_count = len(code_snippet.split("\n"))
            if line_count > SEARCH_CONFIG["chunking_threshold"]:
                return True

    return False


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
        logger.debug(f"📦 DEBUG: Processing node {i+1}/{len(nodes)}")
        logger.debug(f"📦 DEBUG: Node keys: {list(node.keys())}")

        if code_content:
            node_lines = len(str(code_content).split("\n"))
            logger.debug(
                f"📦 DEBUG: Node {i+1} has {node_lines} lines, current total: {total_lines}"
            )

            # Check if adding this node would exceed the limit
            if total_lines + node_lines > line_limit and batch_nodes:
                logger.debug(
                    f"📦 DEBUG: Adding node {i+1} would exceed limit ({total_lines + node_lines} > {line_limit}), stopping batch"
                )
                # Don't add this node, return current batch
                break

            batch_nodes.append(node)
            total_lines += node_lines
            logger.debug(
                f"📦 DEBUG: Added node {i+1} to batch, new total lines: {total_lines}"
            )
        else:
            logger.debug(f"📦 DEBUG: Node {i+1} has no code content, adding anyway")
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

            message = f"Found 1 node with {original_file_lines} total lines. Showing lines {start_line}:{end_line}."
            if chunk_num < total_chunks:
                message += _get_fetch_next_code_note()
        else:
            message = f"Found 1 node with {total_lines} total lines. Showing lines 1 to {delivered_lines}."
            if delivered_lines < total_lines:
                message += _get_fetch_next_code_note()
    else:
        # For multiple nodes, check if we have chunk info to show line ranges
        if chunk_info:
            start_line = chunk_info.get("start_line", 1)
            end_line = chunk_info.get("end_line", delivered_lines)
            chunk_num = chunk_info.get("chunk_num", 1)
            total_chunks = chunk_info.get("total_chunks", 1)
            original_file_lines = chunk_info.get("original_file_lines", total_lines)

            # Show actual line range instead of just counts
            message = f"Found {total_nodes} nodes with {original_file_lines} total lines. Showing lines {start_line}:{end_line}."
            if chunk_num < total_chunks:
                message += _get_fetch_next_code_note()
        else:
            # Fallback to original format when no chunk info available
            message = f"Found {total_nodes} nodes with {total_lines} total lines. Delivered {delivered_nodes} nodes ({delivered_lines} lines)."
            if remaining_nodes > 0:
                message += _get_fetch_next_code_note()

    return message


def calculate_optimal_batch_size(
    nodes: List[Dict[str, Any]], max_lines: int = 500, default_batch_size: int = 15
) -> int:
    """
    Calculate optimal batch size based on content length.

    Args:
        nodes: List of nodes to analyze
        max_lines: Maximum lines allowed per batch
        default_batch_size: Default batch size if no content analysis needed

    Returns:
        Optimal batch size
    """
    if not nodes:
        return default_batch_size

    # Sample first few nodes to estimate average lines per node
    sample_size = min(3, len(nodes))
    total_sample_lines = 0

    for i in range(sample_size):
        node = nodes[i]
        content = node.get("code_snippet", "") or node.get("data", "")
        if content:
            lines = len(str(content).split("\n"))
            total_sample_lines += lines

    if total_sample_lines == 0:
        return default_batch_size

    avg_lines_per_node = total_sample_lines / sample_size
    optimal_batch_size = max(1, int(max_lines / avg_lines_per_node))

    # Cap at default batch size to avoid too large batches
    return min(optimal_batch_size, default_batch_size)


def track_delivery_progress(
    delivered_count: int,
    total_count: int,
    current_lines: int,
    estimated_total_lines: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Track and format delivery progress information.

    Args:
        delivered_count: Number of items delivered
        total_count: Total number of items
        current_lines: Lines in current delivery
        estimated_total_lines: Estimated total lines (optional)

    Returns:
        Dictionary with progress information
    """
    progress_info = {
        "delivered_count": delivered_count,
        "total_count": total_count,
        "remaining_count": max(0, total_count - delivered_count),
        "current_lines": current_lines,
        "progress_percentage": (
            (delivered_count / total_count * 100) if total_count > 0 else 0
        ),
    }

    if estimated_total_lines:
        progress_info["estimated_total_lines"] = estimated_total_lines
        progress_info["estimated_remaining_lines"] = max(
            0, estimated_total_lines - current_lines
        )

    return progress_info


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


def build_enhanced_fetch_note(
    remaining_items: int,
    item_type: str = "nodes",
    estimated_lines: Optional[int] = None,
) -> str:
    """
    Build enhanced fetch next code note with additional context.

    Args:
        remaining_items: Number of remaining items
        item_type: Type of items (nodes, chunks, etc.)
        estimated_lines: Estimated remaining lines

    Returns:
        Enhanced fetch note message
    """
    base_note = _get_fetch_next_code_note()

    if remaining_items > 0:
        context = f" ({remaining_items} more {item_type}"
        if estimated_lines:
            context += f", ~{estimated_lines} lines"
        context += " available)"
        return base_note + context

    return base_note


def enhance_semantic_search_event(
    event: Dict[str, Any], action_parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enhance semantic search event with dynamic guidance.

    Args:
        event: The original event from semantic search
        action_parameters: Parameters from the action

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

    guidance_message = f"Found {total_nodes} nodes from semantic search. Showing nodes {start_node} to {end_node}"

    if current_lines > 0:
        guidance_message += f" ({current_lines} lines)"

    if remaining_count > 0:
        guidance_message += build_enhanced_fetch_note(
            remaining_items=remaining_count,
            item_type="nodes",
            estimated_lines=(
                current_lines * remaining_count if current_lines > 0 else None
            ),
        )
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
        action_parameters: Parameters from the action
        delivery_context: Optional context about delivery state

    Returns:
        Enhanced event with guidance
    """
    total_nodes = event.get("total_nodes", 0)
    data = event.get("data", "")

    if total_nodes == 0 or not data:
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

    if total_nodes == 1:
        # Single node scenario
        chunk_info = delivery_context.get("chunk_info") if delivery_context else None

        if chunk_info:
            # We have chunk info, so this is definitely chunked content
            start_line = chunk_info.get("start_line", 1)
            end_line = chunk_info.get("end_line", current_lines)
            chunk_num = chunk_info.get("chunk_num", 1)
            total_chunks = chunk_info.get("total_chunks", 1)
            original_file_lines = chunk_info.get("original_file_lines", total_lines)

            guidance_message = f"Found 1 node with {original_file_lines} total lines. Showing lines {start_line}:{end_line}."
            if chunk_num < total_chunks:
                guidance_message += _get_fetch_next_code_note()
        elif should_chunk_delivery(data):
            # Fallback to content-based chunking detection
            guidance_message = f"Found 1 node with {total_lines} total lines. Showing lines 1 to {current_lines}."
            if current_lines < total_lines:
                guidance_message += _get_fetch_next_code_note()
        else:
            guidance_message = f"Found 1 node with {current_lines} lines (complete)."
    else:
        # Multiple nodes scenario - use enhanced guidance with actual line info
        # Check if we have chunk info to show line ranges instead of just counts
        chunk_info = delivery_context.get("chunk_info") if delivery_context else None

        # Use original file lines from chunk_info if available
        actual_total_lines = total_lines
        if chunk_info and "original_file_lines" in chunk_info:
            actual_total_lines = chunk_info.get("original_file_lines", total_lines)

        guidance_message = build_database_guidance_with_line_info(
            total_nodes=total_nodes,
            delivered_nodes=delivered_nodes,
            total_lines=actual_total_lines,
            delivered_lines=current_lines,
            remaining_nodes=remaining_nodes,
            chunk_info=chunk_info,
        )

    # Add guidance as prefix to data
    event = GuidanceFormatter.add_prefix_to_data(event, guidance_message)
    return event


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
    - Provide dynamic guidance for batch delivery with node and line information
    """

    def on_event(self, event: Dict[str, Any], action) -> Optional[Dict[str, Any]]:
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

        # Use the enhanced guidance function
        scenario = determine_guidance_scenario(
            total_nodes=total_nodes,
            include_code=True,
        )

        return build_guidance_message(
            search_type=SearchType.SEMANTIC,
            scenario=scenario,
            total_nodes=total_nodes,
            delivered_count=delivered_count,
            remaining_count=remaining_count,
            has_more_results=remaining_count > 0,
        )


class DatabaseSearchGuidance(BaseToolGuidance):
    """
    Guidance handler for database search tool.

    Responsibilities:
    - Generate error guidance for failed queries
    - Handle no results scenarios
    - Provide dynamic guidance for batch delivery with line counting
    """

    def on_event(self, event: Dict[str, Any], action) -> Optional[Dict[str, Any]]:
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
        return total_nodes > 0 and has_code_snippet

    def _build_database_batch_guidance(self, event: Dict[str, Any]) -> Optional[str]:
        """Build guidance message for database batch delivery with line counting."""
        data = event.get("data", "")
        total_nodes = event.get("total_nodes", 0)

        if not data or total_nodes == 0:
            return None

        # Calculate line information
        delivered_lines = len(str(data).split("\n")) if data else 0

        # For database queries, we need to estimate or track total lines
        # This is a simplified approach - in practice you'd track this in the delivery system
        estimated_total_lines = (
            delivered_lines * total_nodes if total_nodes > 1 else delivered_lines
        )

        # Check if this is likely a chunked/batched delivery
        result = event.get("result", "")
        is_chunked = (
            "chunk" in str(result).lower()
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
            )

        return None

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
