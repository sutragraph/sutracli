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
    # First try to get start_line and end_line directly from node
    start_line = node.get("start_line")
    end_line = node.get("end_line")

    # If not found, try to extract from lines field
    if start_line is None or end_line is None:
        lines = node.get("lines")
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
    if node.get("file_path"):
        result_parts.append(f'file_path: {node.get("file_path", "unknown")}')

    # Show block_id if available, otherwise show file info
    block_id = node.get("id", node.get("block_id"))
    if block_id:
        result_parts.append(f"block_id: {block_id}")
        # Add block type and name if available (for GET_BLOCK_DETAILS)
        block_type = node.get("type")
        block_name = node.get("name")
        if block_type:
            result_parts.append(f"block_type: {block_type}")
        if block_name:
            result_parts.append(f"block_name: {block_name}")
    else:
        result_parts.append(f'file_id: {node.get("file_id", "unknown")}')

    # Format start_line:end_line - use chunk info if available, otherwise node info
    if chunk_info:
        # Use chunk-specific line range when chunking is active
        chunk_start = chunk_info.get("start_line", start_line)
        chunk_end = chunk_info.get("end_line", end_line)
        start_end_str = f"{chunk_start}:{chunk_end}"
    elif start_line is not None and end_line is not None:
        start_end_str = f"{start_line}:{end_line}"
    else:
        # For file queries, try to get line count from content
        content = node.get("content", node.get("code_snippet", ""))
        if content:
            line_count = len(content.split("\n"))
            start_end_str = f"1:{line_count}"
        else:
            start_end_str = "unknown"
    result_parts.append(f"start_line:end_line: {start_end_str}")

    # Add parent block details section if available (for GET_BLOCK_DETAILS)
    parent = node.get("parent")
    parent_children = node.get("parent_children", [])
    if parent:
        result_parts.append("parent_block_details:")
        result_parts.append(f'  parent_id: {parent.get("id", "unknown")}')
        result_parts.append(f'  parent_type: {parent.get("type", "unknown")}')
        result_parts.append(f'  parent_name: {parent.get("name", "unknown")}')
        result_parts.append(
            f'  parent_lines: {parent.get("start_line", "?")}:{parent.get("end_line", "?")}'
        )

        # Add all children of the parent block
        if parent_children:
            result_parts.append(
                f"  parent_children: {len(parent_children)} child blocks"
            )
            for i, child in enumerate(parent_children, 1):
                child_id = child.get("id", "unknown")
                child_type = child.get("type", "unknown")
                child_name = child.get("name", "unknown")
                child_lines = (
                    f'{child.get("start_line", "?")}:{child.get("end_line", "?")}'
                )
                result_parts.append(
                    f"    child_{i}: id={child_id}, type={child_type}, name={child_name}, lines={child_lines}"
                )

    # Add connection information if available (for GET_BLOCK_DETAILS)
    incoming_connections = node.get("incoming_connections", [])
    outgoing_connections = node.get("outgoing_connections", [])
    total_connections = len(incoming_connections) + len(outgoing_connections)

    if total_connections > 0:
        result_parts.append(f"connections_found: {total_connections}")

        # Display incoming connections
        if incoming_connections:
            result_parts.append(f"incoming_connections: {len(incoming_connections)}")
            for i, conn in enumerate(incoming_connections, 1):
                description = conn.get("description", "No description")
                technology = conn.get("technology_name", "unknown")
                source_file = conn.get("source_file_path", "unknown")
                result_parts.append(f"  incoming_{i}: [{technology}] {description}")
                result_parts.append(f"    from_file: {source_file}")

                # Add code snippet if available
                code_snippet = conn.get("code_snippet", "")
                if code_snippet and code_snippet.strip():
                    # Truncate long code snippets for readability
                    lines = code_snippet.strip().split("\n")
                    if len(lines) > 5:
                        snippet_preview = (
                            "\n".join(lines[:3])
                            + "\n    ... ("
                            + str(len(lines) - 3)
                            + " more lines)"
                        )
                    else:
                        snippet_preview = code_snippet.strip()
                    result_parts.append(f"    code: {snippet_preview}")

        # Display outgoing connections
        if outgoing_connections:
            result_parts.append(f"outgoing_connections: {len(outgoing_connections)}")
            for i, conn in enumerate(outgoing_connections, 1):
                description = conn.get("description", "No description")
                technology = conn.get("technology_name", "unknown")
                target_file = conn.get("target_file_path", "unknown")
                result_parts.append(f"  outgoing_{i}: [{technology}] {description}")
                result_parts.append(f"    to_file: {target_file}")

                # Add code snippet if available
                code_snippet = conn.get("code_snippet", "")
                if code_snippet and code_snippet.strip():
                    # Truncate long code snippets for readability
                    lines = code_snippet.strip().split("\n")
                    if len(lines) > 5:
                        snippet_preview = (
                            "\n".join(lines[:3])
                            + "\n    ... ("
                            + str(len(lines) - 3)
                            + " more lines)"
                        )
                    else:
                        snippet_preview = code_snippet.strip()
                    result_parts.append(f"    code: {snippet_preview}")

    # Add hierarchy path if available (for GET_FILE_BLOCK_SUMMARY results)
    hierarchy_path = node.get("hierarchy_path")
    if hierarchy_path and isinstance(hierarchy_path, list) and len(hierarchy_path) > 0:
        path_parts = []
        for path_node in hierarchy_path:
            id = path_node.get("id", "unknown")
            name = path_node.get("name", "unknown")
            node_type = path_node.get("type", "unknown")
            start_line = path_node.get("start_line", "unknown")
            end_line = path_node.get("end_line", "unknown")
            path_parts.append(
                f"id={id}, name={name}, type={node_type}, lines={start_line}:{end_line}"
            )
        hierarchy_str = " → ".join(path_parts)
        result_parts.append(f"hierarchy_path: {hierarchy_str}")

    # Add code snippet if requested and available
    if include_code:
        # For GET_FILE_BY_PATH, the content is in 'content' field, for other queries it's in 'code_snippet'
        code_snippet = node.get("content", node.get("code_snippet", ""))
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

    return "\n".join(result_parts)


def beautify_node_result_metadata_only(node, idx=None, total_nodes=None):
    """
    Format node result with only essential metadata (no code content).

    Args:
        node: Node data dictionary
        idx: Node index number
        total_nodes: Total number of nodes being sent (for guidance)
    """
    start_line = node.get("start_line")
    end_line = node.get("end_line")

    # If not found, try to extract from lines field
    if start_line is None or end_line is None:
        lines = node.get("lines")
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
            header = f"=== NODE {idx} of {total_nodes} ==="
        else:
            header = f"=== NODE {idx} ==="
    else:
        header = "=== NODE ==="

    # Format start_line:end_line
    if start_line is not None and end_line is not None:
        start_end_str = f"{start_line}:{end_line}"
    else:
        # For file queries, try to get line count from content
        content = node.get("content", node.get("code_snippet", ""))
        if content:
            line_count = len(content.split("\n"))
            start_end_str = f"1:{line_count}"
        else:
            start_end_str = "unknown"

    # Show block_id if available, otherwise show file info
    block_id = node.get("id", node.get("block_id"))
    if block_id:
        id_info = f"block_id: {block_id}"
        # Add block type and name if available
        block_type = node.get("type")
        block_name = node.get("name")
        type_info = f"block_type: {block_type}" if block_type else ""
        name_info = f"block_name: {block_name}" if block_name else ""
    else:
        id_info = f'file_id: {node.get("file_id", "unknown")}'
        type_info = ""
        name_info = ""

    # Build the result
    result_parts = [header, f'file_path: {node.get("file_path", "unknown")}', id_info]

    if type_info:
        result_parts.append(type_info)
    if name_info:
        result_parts.append(name_info)

    result_parts.append(f"start_line:end_line: {start_end_str}")

    # Add hierarchy path if available (for GET_FILE_BLOCK_SUMMARY results)
    hierarchy_path = node.get("hierarchy_path")
    if hierarchy_path and isinstance(hierarchy_path, list) and len(hierarchy_path) > 0:
        path_parts = []
        for path_node in hierarchy_path:
            id = path_node.get("id", "unknown")
            name = path_node.get("name", "unknown")
            node_type = path_node.get("type", "unknown")
            start_line_path = path_node.get("start_line", "unknown")
            end_line_path = path_node.get("end_line", "unknown")
            path_parts.append(
                f"id={id}, name={name}, type={node_type}, lines={start_line_path}:{end_line_path}"
            )
        hierarchy_str = " -> ".join(path_parts)
        result_parts.append(f"hierarchy_path: {hierarchy_str}")

    return "\n".join(result_parts)
