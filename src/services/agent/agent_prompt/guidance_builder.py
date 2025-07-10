"""
Guidance builder for providing contextual guidance messages to the agent.
This module provides enums and functions for building guidance messages
based on different search scenarios and results.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from src.services.agent.tool_action_executor.utils.constants import GUIDANCE_MESSAGES, SEARCH_CONFIG


def _get_fetch_next_code_note() -> str:
    """
    Helper function to generate the fetch_next_code note.

    Returns:
        Formatted note about fetching next code
    """
    return GUIDANCE_MESSAGES["FETCH_NEXT_CODE_NOTE"]


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
        return GUIDANCE_MESSAGES["NO_RESULTS_FOUND"].format(search_type=search_type.value)

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


def build_sequential_node_message(
    scenario: SequentialNodeScenario, node_index: int, total_nodes: int, **kwargs
) -> str:
    """
    Build guidance message for sequential node delivery.

    Args:
        scenario: Sequential node scenario
        node_index: Current node index (1-based)
        total_nodes: Total number of nodes
        **kwargs: Additional parameters

    Returns:
        Formatted guidance message
    """
    if scenario == SequentialNodeScenario.NODE_WITH_SMALL_CODE:
        message = f"Node {node_index}/{total_nodes}: Complete code content"
        if node_index < total_nodes:
            message += _get_fetch_next_code_note()
        return message

    elif scenario == SequentialNodeScenario.NODE_WITH_LARGE_CODE_FIRST_CHUNK:
        chunk_num = kwargs.get("chunk_num", 1)
        total_chunks = kwargs.get("total_chunks", 1)
        message = f"Node {node_index}/{total_nodes}: Large file - Chunk {chunk_num}/{total_chunks} (First chunk)"
        if chunk_num < total_chunks or node_index < total_nodes:
            message += _get_fetch_next_code_note()
        return message

    elif scenario == SequentialNodeScenario.NODE_WITH_LARGE_CODE_MIDDLE_CHUNK:
        chunk_num = kwargs.get("chunk_num", 1)
        total_chunks = kwargs.get("total_chunks", 1)
        message = f"Node {node_index}/{total_nodes}: Large file - Chunk {chunk_num}/{total_chunks} (Middle chunk)"
        if chunk_num < total_chunks or node_index < total_nodes:
            message += _get_fetch_next_code_note()
        return message

    elif scenario == SequentialNodeScenario.NODE_WITH_LARGE_CODE_LAST_CHUNK:
        chunk_num = kwargs.get("chunk_num", 1)
        total_chunks = kwargs.get("total_chunks", 1)
        message = f"Node {node_index}/{total_nodes}: Large file - Chunk {chunk_num}/{total_chunks} (Last chunk)"
        if node_index < total_nodes:
            message += _get_fetch_next_code_note()
        return message

    elif scenario == SequentialNodeScenario.NODE_NO_CODE_CONTENT:
        message = f"Node {node_index}/{total_nodes}: No code content available"
        if node_index < total_nodes:
            message += _get_fetch_next_code_note()
        return message

    return f"Node {node_index}/{total_nodes}"


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
