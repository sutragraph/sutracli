from typing import Dict, List, Any
from .constants import GUIDANCE_MESSAGES
from services.agent.agent_prompt.guidance_builder import (
    SearchType,
    determine_guidance_scenario,
    build_guidance_message,
)


def build_batch_guidance_message(
    search_type: SearchType,
    total_nodes: int,
    include_code: bool,
    has_large_files: bool = False,
    current_node: int = 1,
    has_more_nodes: bool = False,
    **kwargs
) -> str:
    """
    Build guidance message for batch processing.

    Args:
        search_type: Type of search (semantic or database)
        total_nodes: Total number of nodes
        include_code: Whether code content is included
        has_large_files: Whether any files are large
        current_node: Current node being processed
        has_more_nodes: Whether there are more nodes available
        **kwargs: Additional parameters for guidance formatting

    Returns:
        str: Formatted guidance message
    """
    # Extract parameters that are valid for determine_guidance_scenario
    scenario_params = {
        "total_nodes": total_nodes,
        "include_code": include_code,
    }

    # Add optional parameters if they exist in kwargs
    if "code_lines" in kwargs:
        scenario_params["code_lines"] = kwargs["code_lines"]
    if "chunk_info" in kwargs:
        scenario_params["chunk_info"] = kwargs["chunk_info"]
    if "is_line_filtered" in kwargs:
        scenario_params["is_line_filtered"] = kwargs["is_line_filtered"]

    guidance_scenario = determine_guidance_scenario(**scenario_params)

    guidance_message = build_guidance_message(
        search_type=search_type,
        scenario=guidance_scenario,
        total_nodes=total_nodes,
        current_node=current_node,
        has_more_nodes=has_more_nodes,
        **kwargs
    )

    return guidance_message + "\n\n" if guidance_message else ""


def extract_keyword_context(
    code_snippet: str, keyword: str, context_lines: int = 10
) -> Dict[str, Any]:
    """
    Extract context lines around a keyword in code snippet.

    Args:
        code_snippet: The full code content
        keyword: The keyword to search for
        context_lines: Number of lines to show before and after the keyword (default: 10)

    Returns:
        Dictionary with context information or None if keyword not found
    """
    if not code_snippet or not keyword:
        return None

    lines = code_snippet.split("\n")
    keyword_lines = []

    # Find all lines containing the keyword
    for line_num, line in enumerate(lines, 1):
        if keyword in line:
            keyword_lines.append(
                {
                    "line_number": line_num,
                    "line_content": line.strip(),
                    "original_line_number": line_num,
                }
            )

    if not keyword_lines:
        return None

    # For now, use the first occurrence
    first_occurrence = keyword_lines[0]
    found_line_num = first_occurrence["line_number"]

    # Calculate context range
    start_line = max(1, found_line_num - context_lines)
    end_line = min(len(lines), found_line_num + context_lines)

    # Extract context lines
    context_lines_data = []
    for i in range(start_line - 1, end_line):  # -1 because lines array is 0-indexed
        line_num = i + 1
        is_keyword_line = line_num == found_line_num
        context_lines_data.append(
            {
                "line_number": line_num,
                "content": lines[i],
                "is_keyword_line": is_keyword_line,
            }
        )

    return {
        "keyword": keyword,
        "found_at_line": found_line_num,
        "context_start_line": start_line,
        "context_end_line": end_line,
        "total_lines": len(lines),
        "context_lines": context_lines_data,
        "all_occurrences": keyword_lines,
    }


def format_context_snippet(context_info: Dict[str, Any]) -> str:
    """
    Format context information into a readable code snippet.

    Args:
        context_info: Context information from extract_keyword_context

    Returns:
        Formatted string with line numbers and context
    """
    if not context_info:
        return ""

    lines = []
    lines.append(
        f"Found '{context_info['keyword']}' at line {context_info['found_at_line']}"
    )
    lines.append(
        f"Context (lines {context_info['context_start_line']}-{context_info['context_end_line']} of {context_info['total_lines']} total):"
    )
    lines.append("")

    for line_data in context_info["context_lines"]:
        line_num = line_data["line_number"]
        content = line_data["content"]
        lines.append(f"     {line_num:4d} | {content}")

    return "\n".join(lines)


def process_keyword_search_results(
    results: List[Dict[str, Any]], keyword: str, context_lines: int = 10
) -> List[Dict[str, Any]]:
    """
    Process keyword search results to include context information.

    Args:
        results: Raw database query results
        keyword: The searched keyword
        context_lines: Number of context lines to extract

    Returns:
        Processed results with context information
    """
    processed_results = []

    for result in results:
        processed_result = result.copy()

        # Extract context if code snippet is available and contains the keyword
        code_snippet = result.get("code_snippet", "")
        if code_snippet and keyword in code_snippet:
            context_info = extract_keyword_context(code_snippet, keyword, context_lines)
            if context_info:
                processed_result["keyword_context"] = context_info
                processed_result["formatted_context"] = format_context_snippet(
                    context_info
                )
                # Replace full code snippet with context snippet for delivery
                processed_result["code_snippet"] = processed_result["formatted_context"]

        processed_results.append(processed_result)

    return processed_results


def create_delivery_batches(
    results: List[Dict[str, Any]], batch_size: int
) -> List[List[Dict[str, Any]]]:
    """
    Split results into batches for delivery queue.

    Args:
        results: List of results to batch
        batch_size: Number of items per batch

    Returns:
        List of batches
    """
    batches = []
    for i in range(0, len(results), batch_size):
        batch = results[i : i + batch_size]
        batches.append(batch)
    return batches


def build_delivery_info(
    current_batch: int,
    total_batches: int,
    batch_size: int,
    total_results: int,
    has_code: bool = True,
) -> Dict[str, Any]:
    """
    Build delivery information for batch processing.

    Args:
        current_batch: Current batch number (1-indexed)
        total_batches: Total number of batches
        batch_size: Size of each batch
        total_results: Total number of results
        has_code: Whether results include code content

    Returns:
        Delivery information dictionary
    """
    current_start = (current_batch - 1) * batch_size + 1
    current_end = min(current_batch * batch_size, total_results)
    has_more = current_batch < total_batches

    return {
        "current_batch": current_batch,
        "total_batches": total_batches,
        "current_start": current_start,
        "current_end": current_end,
        "total_results": total_results,
        "batch_size": batch_size,
        "has_more": has_more,
        "has_code": has_code,
        "delivery_type": "code_with_context" if has_code else "metadata_only",
    }


def format_delivery_guidance(
    delivery_info: Dict[str, Any], search_type: str = "keyword"
) -> str:
    """
    Format guidance message for delivery batches.

    Args:
        delivery_info: Delivery information from build_delivery_info
        search_type: Type of search (keyword, exact_name, etc.)

    Returns:
        Formatted guidance message
    """
    current_batch = delivery_info["current_batch"]
    total_batches = delivery_info["total_batches"]
    current_start = delivery_info["current_start"]
    current_end = delivery_info["current_end"]
    total_results = delivery_info["total_results"]
    has_more = delivery_info["has_more"]
    delivery_type = delivery_info["delivery_type"]

    if delivery_type == "code_with_context":
        guidance = f"KEYWORD SEARCH RESULTS: Showing {search_type} search results {current_start}-{current_end} of {total_results} total results (batch {current_batch}/{total_batches})"
        if has_more:
            guidance += GUIDANCE_MESSAGES["FETCH_NEXT_CODE_NOTE"]
    else:
        guidance = f"METADATA SEARCH RESULTS: Showing {search_type} search results {current_start}-{current_end} of {total_results} total results (batch {current_batch}/{total_batches})"
        if has_more:
            guidance += GUIDANCE_MESSAGES["FETCH_NEXT_CODE_NOTE"]

    return guidance
