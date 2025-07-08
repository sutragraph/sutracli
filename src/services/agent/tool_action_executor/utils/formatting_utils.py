"""
Formatting utility functions for beautifying node results and output.
"""

import json


def beautify_node_result(
    node, idx=None, include_code=True, total_nodes=None, chunk_info=None
):
    """
    Format node result with optional code inclusion and chunking information.

    Args:
        node: Node data dictionary
        idx: Node index number
        include_code: Whether to include code snippet
        total_nodes: Total number of nodes being sent (for guidance)
        chunk_info: Dictionary with chunk information (chunk_num, total_chunks, start_line, end_line, total_lines)
    """
    lines = node.get("lines")
    start_line, end_line = None, None
    if lines:
        if isinstance(lines, list) and len(lines) >= 2:
            # Lines is already a list [start_line, end_line]
            start_line, end_line = lines[0], lines[1]
        elif isinstance(lines, str):
            try:
                lines_data = json.loads(lines)
                if isinstance(lines_data, list) and len(lines_data) >= 2:
                    start_line, end_line = lines_data[0], lines_data[1]
            except (json.JSONDecodeError, ValueError):
                pass

    # Build result parts
    result_parts = []

    # Add node header with index if provided
    if idx is not None:
        if total_nodes:
            result_parts.append(f"=== NODE {idx} of {total_nodes} ===")
        else:
            result_parts.append(f"=== NODE {idx} ===")
    else:
        result_parts.append("=== NODE ===")

    # Add chunk information if provided
    if chunk_info:
        chunk_num = chunk_info.get("chunk_num", 1)
        total_chunks = chunk_info.get("total_chunks", 1)
        chunk_start = chunk_info.get(
            "chunk_start_line", chunk_info.get("start_line", start_line)
        )
        chunk_end = chunk_info.get(
            "chunk_end_line", chunk_info.get("end_line", end_line)
        )

        # Get the total lines of the original file (not the chunk)
        # This should be the total lines of the entire file being chunked
        original_file_lines = chunk_info.get(
            "original_file_lines", chunk_info.get("total_lines", "unknown")
        )

        result_parts.append(
            f"CHUNK {chunk_num} of {total_chunks} (lines {chunk_start}-{chunk_end} of {original_file_lines} total)"
        )

    # Add basic node information
    result_parts.append(f'file_path: {node.get("file_path", "unknown")}')
    result_parts.append(f'node_name: {node.get("name", "unknown")}')

    # Format start_line:end_line
    if start_line is not None and end_line is not None:
        start_end_str = f"{start_line}:{end_line}"
    else:
        start_end_str = "unknown"
    result_parts.append(f"start_line:end_line: {start_end_str}")

    result_parts.append(f'node_type: {node.get("type", node.get("node_type", "unknown"))}')

    # Add code snippet if requested and available
    if include_code:
        code_snippet = node.get("code_snippet", "")
        if code_snippet and code_snippet.strip():
            result_parts.append("code_snippet:")

            # Add line numbers if not already present
            if not any(
                line.strip() and line.strip()[0].isdigit() and " |" in line
                for line in code_snippet.split("\n")[:3]
            ):
                # Code doesn't have line numbers, add them
                from .code_processing_utils import add_line_numbers_to_code

                # Use start_line from node if available, otherwise default to 1
                file_start_line = start_line if start_line is not None else 1
                numbered_code = add_line_numbers_to_code(code_snippet, file_start_line)
                result_parts.append(numbered_code)
            else:
                # Code already has line numbers
                result_parts.append(code_snippet)
        else:
            result_parts.append("code_snippet:\n(no code available)")

    return "\n".join(result_parts)


def beautify_node_result_metadata_only(node, idx=None, total_nodes=None):
    """
    Format node result with only essential metadata (no code content).

    Args:
        node: Node data dictionary
        idx: Node index number
        total_nodes: Total number of nodes being sent (for guidance)
    """
    lines = node.get("lines")
    start_line, end_line = None, None
    if lines:
        if isinstance(lines, list) and len(lines) >= 2:
            # Lines is already a list [start_line, end_line]
            start_line, end_line = lines[0], lines[1]
        elif isinstance(lines, str):
            try:
                lines_data = json.loads(lines)
                if isinstance(lines_data, list) and len(lines_data) >= 2:
                    start_line, end_line = lines_data[0], lines_data[1]
            except (json.JSONDecodeError, ValueError):
                pass

    # Build header with index if provided
    if idx is not None:
        if total_nodes:
            header = f"=== NODE {idx} of {total_nodes} (metadata only) ==="
        else:
            header = f"=== NODE {idx} (metadata only) ==="
    else:
        header = "=== NODE (metadata only) ==="

    # Format start_line:end_line
    if start_line is not None and end_line is not None:
        start_end_str = f"{start_line}:{end_line}"
    else:
        start_end_str = "unknown"

    return (
        f"{header}\n"
        f'file_path: {node.get("file_path", "unknown")}\n'
        f'node_name: {node.get("name", "unknown")}\n'
        f"start_line:end_line: {start_end_str}\n"
        f'node_type: {node.get("type", node.get("node_type", "unknown"))}'
    )
