"""
Utilities for formatting and beautifying enriched context data from graph operations.

This module provides functions to format the rich context data returned by
GraphOperations.get_enriched_block_context() and GraphOperations.get_enriched_file_context()
into human-readable, structured text for display in search results and agent responses.
"""

from typing import Dict, Any, List, Optional
from tools.utils.code_processing_utils import add_line_numbers_to_code


def _format_node_id_display(node_id: Optional[str]) -> str:
    """
    Extract and format node_id for display.

    Args:
        node_id: Node identifier (e.g., 'block_123', 'file_456', 'block_123_chunk_0')

    Returns:
        Formatted string like ' | Block ID: 123' or ' | File ID: 456'
    """
    if not node_id:
        return ""

    if node_id.startswith("block_"):
        # Handle both 'block_123' and 'block_123_chunk_0' formats
        extracted_id = node_id.split("_")[1]
        return f" | Block ID: {extracted_id}"
    elif node_id.startswith("file_"):
        # Handle both 'file_456' and 'file_456_chunk_0' formats
        extracted_id = node_id.split("_")[1]
        return f" | File ID: {extracted_id}"
    else:
        return f" | Node ID: {node_id}"


def beautify_enriched_block_context(
    enriched_context: Dict[str, Any],
    index: int = 1,
    total_nodes: int = 1,
    include_code: bool = True,
    max_code_lines: Optional[int] = None,
    node_id: Optional[str] = None
) -> str:
    """
    Format enriched block context into a beautiful, readable string.

    Args:
        enriched_context: Result from GraphOperations.get_enriched_block_context()
        index: Position in search results
        total_nodes: Total number of results
        include_code: Whether to include code content
        max_code_lines: Maximum lines of code to display
        node_id: Optional node identifier (e.g., 'block_123' or 'file_456')

    Returns:
        Formatted string representation
    """
    if not enriched_context:
        return f"Node {index}/{total_nodes}: No context available"

    block = enriched_context.get('block', {})
    file_context = enriched_context.get('file_context', {})

    parent_block = enriched_context.get('parent_block')
    child_blocks = enriched_context.get('child_blocks', [])

    # Header
    result_parts = []
    header = f"Chunk: {index}/{total_nodes}" + _format_node_id_display(node_id)
    result_parts.append(header)

    # Block information
    block_type = block.get('type', 'unknown').title()
    block_name = block.get('name', 'unnamed')
    result_parts.append(f"{block_type}: `{block_name}`")

    # File context
    file_path = file_context.get("file_path", "unknown")
    result_parts.append(f"File: {file_path}")

    # Line information
    start_line = block.get('start_line')
    end_line = block.get('end_line')
    if start_line and end_line:
        line_count = end_line - start_line + 1
        result_parts.append(
            f"Block Lines: {start_line}-{end_line} ({line_count} lines)"
        )

    # Hierarchy information
    if parent_block:
        parent_name = parent_block.get('name', 'unnamed')
        parent_type = parent_block.get('type', 'unknown')
        result_parts.append(f"Parent: {parent_type} `{parent_name}`")

    if child_blocks:
        child_count = len(child_blocks)
        child_names = [f"`{child.get('name', 'unnamed')}`" for child in child_blocks[:3]]
        child_summary = ", ".join(child_names)
        if child_count > 3:
            child_summary += f" ... (+{child_count - 3} more)"
        result_parts.append(f"Children ({child_count}): {child_summary}")

    # Connection details - show both mappings and remaining basic connections
    connection_mappings = enriched_context.get('connection_mappings', [])
    connections = enriched_context.get('connections', {})
    incoming_conns = connections.get('incoming', [])
    outgoing_conns = connections.get('outgoing', [])

    if connection_mappings or incoming_conns or outgoing_conns:
        if connection_mappings:
            # Show detailed connection mappings first
            result_parts.append("Connections:")
            result_parts.append("")
            mapping_lines = _format_connection_mappings(connection_mappings)
            result_parts.extend(mapping_lines)

        # Show remaining basic connections if any
        if incoming_conns or outgoing_conns:
            if connection_mappings:
                # Add separator if we already showed mappings
                result_parts.append("Additional connections:\n")
            else:
                result_parts.append(f"Connections: {len(incoming_conns)} incoming | {len(outgoing_conns)} outgoing")

            # Show detailed incoming connections grouped by technology
            if incoming_conns:
                result_parts.append("Incoming connections:")
                grouped_incoming = _group_connections_by_technology(incoming_conns, "incoming")
                tech_count = 0
                for technology, tech_connections in grouped_incoming.items():
                    if tech_count >= 3:  # Limit to 3 technology groups
                        remaining_techs = len(grouped_incoming) - tech_count
                        result_parts.append(f"   ... and {remaining_techs} more technologies")
                        break
                    conn_lines = _format_grouped_connections(technology, tech_connections, "incoming")
                    if conn_lines:
                        result_parts.extend(conn_lines)
                        result_parts.append("")  # Add spacing between technology groups
                    tech_count += 1

            # Show detailed outgoing connections grouped by technology
            if outgoing_conns:
                result_parts.append("Outgoing connections:")
                grouped_outgoing = _group_connections_by_technology(outgoing_conns, "outgoing")
                tech_count = 0
                for technology, tech_connections in grouped_outgoing.items():
                    if tech_count >= 3:  # Limit to 3 technology groups
                        remaining_techs = len(grouped_outgoing) - tech_count
                        result_parts.append(f"   ... and {remaining_techs} more technologies")
                        break
                    conn_lines = _format_grouped_connections(technology, tech_connections, "outgoing")
                    if conn_lines:
                        result_parts.extend(conn_lines)
                        result_parts.append("")  # Add spacing between technology groups
                    tech_count += 1

    # Code content
    if include_code and block.get("content"):
        result_parts.append("Code:")

        content = block['content']
        if max_code_lines and len(content.split('\n')) > max_code_lines:
            lines = content.split('\n')
            content = '\n'.join(lines[:max_code_lines])
            content += f"\n... ({len(lines) - max_code_lines} more lines)"

        # Add line numbers
        if start_line:
            numbered_code = add_line_numbers_to_code(content, start_line)
            result_parts.append(numbered_code)
        else:
            result_parts.append(content)

    return "\n".join(result_parts)


def beautify_enriched_file_context(
    enriched_context: Dict[str, Any],
    index: int = 1,
    total_nodes: int = 1,
    include_code: bool = True,
    max_code_lines: Optional[int] = None,
    node_id: Optional[str] = None
) -> str:
    """
    Format enriched file context into a beautiful, readable string.

    Args:
        enriched_context: Result from GraphOperations.get_enriched_file_context()
        index: Position in search results
        total_nodes: Total number of results
        include_code: Whether to include code content
        max_code_lines: Maximum lines of code to display
        node_id: Optional node identifier (e.g., 'block_123' or 'file_456')

    Returns:
        Formatted string representation
    """
    if not enriched_context:
        return f"Node {index}/{total_nodes}: No context available"

    file_data = enriched_context.get('file', {})

    # Header
    result_parts = []
    result_parts.append("")
    header = f"Chunk: {index}/{total_nodes}" + _format_node_id_display(node_id)
    result_parts.append(header)

    # File information
    file_path = file_data.get("file_path", "unknown")
    result_parts.append(f"File: {file_path}")

    # Connection details - show both mappings and remaining basic connections
    connection_mappings = enriched_context.get('connection_mappings', [])
    connections = enriched_context.get('connections', {})
    incoming_conns = connections.get('incoming', [])
    outgoing_conns = connections.get('outgoing', [])

    if connection_mappings or incoming_conns or outgoing_conns:
        if connection_mappings:
            # Show detailed connection mappings first
            result_parts.append("Connections:")
            result_parts.append("")
            mapping_lines = _format_connection_mappings(connection_mappings)
            result_parts.extend(mapping_lines)

        # Show remaining basic connections if any
        if incoming_conns or outgoing_conns:
            if connection_mappings:
                # Add separator if we already showed mappings
                result_parts.append("Additional connections:\n")
            else:
                result_parts.append(f"Connections: {len(incoming_conns)} incoming | {len(outgoing_conns)} outgoing")

            # Show detailed incoming connections grouped by technology
            if incoming_conns:
                result_parts.append("Incoming connections:")
                grouped_incoming = _group_connections_by_technology(incoming_conns, "incoming")
                tech_count = 0
                for technology, tech_connections in grouped_incoming.items():
                    if tech_count >= 4:  # Show more for files
                        remaining_techs = len(grouped_incoming) - tech_count
                        result_parts.append(f"   ... and {remaining_techs} more technologies")
                        break
                    conn_lines = _format_grouped_connections(technology, tech_connections, "incoming")
                    if conn_lines:
                        result_parts.extend(conn_lines)
                        result_parts.append("")  # Add spacing between technology groups
                    tech_count += 1

            # Show detailed outgoing connections grouped by technology
            if outgoing_conns:
                result_parts.append("Outgoing connections:")
                grouped_outgoing = _group_connections_by_technology(outgoing_conns, "outgoing")
                tech_count = 0
                for technology, tech_connections in grouped_outgoing.items():
                    if tech_count >= 4:  # Show more for files
                        remaining_techs = len(grouped_outgoing) - tech_count
                        result_parts.append(f"   ... and {remaining_techs} more technologies")
                        break
                    conn_lines = _format_grouped_connections(technology, tech_connections, "outgoing")
                    if conn_lines:
                        result_parts.extend(conn_lines)
                        result_parts.append("")  # Add spacing between technology groups
                    tech_count += 1

    # File content (if requested)
    if include_code and file_data.get('content'):
        result_parts.append("")
        result_parts.append("File Content:")

        content = file_data['content']
        if max_code_lines and len(content.split('\n')) > max_code_lines:
            lines = content.split('\n')
            content = '\n'.join(lines[:max_code_lines])
            content += f"\n... ({len(lines) - max_code_lines} more lines)"

        numbered_code = add_line_numbers_to_code(content, 1)
        result_parts.append(numbered_code)

    return "\n".join(result_parts)


def beautify_enriched_context_auto(
    enriched_context: Dict[str, Any],
    index: int = 1,
    total_nodes: int = 1,
    include_code: bool = True,
    max_code_lines: Optional[int] = None,
    node_id: Optional[str] = None
) -> str:
    """
    Automatically determine whether to format as block or file context.

    Args:
        enriched_context: Result from GraphOperations enriched context functions
        index: Position in search results
        total_nodes: Total number of results
        include_code: Whether to include code content
        max_code_lines: Maximum lines of code to display
        node_id: Optional node identifier (e.g., 'block_123' or 'file_456')

    Returns:
        Formatted string representation
    """
    if not enriched_context:
        return f"Node {index}/{total_nodes}: No context available"

    # Determine type based on presence of 'block' or 'file' key
    if 'block' in enriched_context:
        return beautify_enriched_block_context(
            enriched_context, index, total_nodes, include_code, max_code_lines, node_id
        )
    elif 'file' in enriched_context:
        return beautify_enriched_file_context(
            enriched_context, index, total_nodes, include_code, max_code_lines, node_id
        )
    else:
        node_info = _format_node_id_display(node_id)
        return f"Node {index}/{total_nodes}{node_info}: Unknown context type"


def format_chunk_with_enriched_context(
    enriched_context: Dict[str, Any],
    chunk_start_line: int,
    chunk_end_line: int,
    chunk_code: str,
    index: int = 1,
    total_nodes: int = 1,
    node_id: Optional[str] = None
) -> str:
    """
    Format enriched context with specific chunk information.

    Args:
        enriched_context: Result from GraphOperations enriched context functions
        chunk_start_line: Starting line of the chunk
        chunk_end_line: Ending line of the chunk
        chunk_code: Code content of the specific chunk
        index: Position in search results
        total_nodes: Total number of results
        node_id: Optional node identifier (e.g., 'block_123' or 'file_456')

    Returns:
        Formatted string representation with chunk-specific code
    """
    if not enriched_context:
        return f"Chunk {index}/{total_nodes}: No context available"

    # Get base formatting
    base_format = beautify_enriched_context_auto(
        enriched_context, index, total_nodes, include_code=False, node_id=node_id
    )

    # Add chunk-specific information
    chunk_parts = [base_format]
    line_count = chunk_end_line - chunk_start_line + 1
    chunk_parts.append(
        f"Chunk Lines: {chunk_start_line}-{chunk_end_line} ({line_count} lines)"
    )

    # Add chunk code with line numbers
    chunk_parts.append("Code:")
    numbered_chunk = add_line_numbers_to_code(chunk_code, chunk_start_line)
    chunk_parts.append(numbered_chunk)

    return "\n".join(chunk_parts)


def _group_connections_by_technology(
        connections: List[Dict[str, Any]], direction: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group connections by technology to handle 1-to-many relationships.

    Args:
        connections: List of connection records
        direction: "incoming" or "outgoing"

    Returns:
        Dictionary mapping technology names to lists of connections
    """
    grouped = {}
    for conn in connections:
        technology = conn.get('technology_name', 'Unknown')
        if technology not in grouped:
            grouped[technology] = []
        grouped[technology].append(conn)
    return grouped


def _format_connection_mappings(mappings: List[Dict[str, Any]]) -> List[str]:
    """
    Format connection mappings similar to GET_FILE_BY_PATH output.

    Args:
        mappings: List of connection mapping dictionaries

    Returns:
        List of formatted connection strings
    """
    if not mappings:
        return []

    result_lines = []

    for x, mapping in enumerate(mappings, 1):
        # Get sender and receiver info
        sender_file = mapping.get('sender_file_path', 'unknown')
        sender_project = mapping.get('sender_project', 'unknown')
        sender_snippet = mapping.get('sender_code_snippet', '')
        sender_lines = mapping.get('sender_snippet_lines', '')

        receiver_file = mapping.get('receiver_file_path', 'unknown')
        receiver_project = mapping.get('receiver_project', 'unknown')
        receiver_snippet = mapping.get('receiver_code_snippet', '')
        receiver_lines = mapping.get('receiver_snippet_lines', '')

        technology = mapping.get("technology_name", "Unknown")

        # Add sender info with code snippet
        if sender_snippet and sender_lines:
            result_lines.append(f"{x}.) {sender_file} [project: {sender_project}]")
            # Parse and display code snippet with line numbers
            try:
                import json
                # Handle different input formats for lines_data
                if isinstance(sender_lines, str) and sender_lines.strip():
                    lines_data = json.loads(sender_lines)
                elif isinstance(sender_lines, list):
                    lines_data = sender_lines
                else:
                    lines_data = None

                if isinstance(lines_data, list) and len(lines_data) >= 1:
                    start_line = lines_data[0]
                    snippet_lines = sender_snippet.split('\n')
                    for i, line in enumerate(snippet_lines):
                        result_lines.append(f"{start_line + i} | {line}")
                else:
                    result_lines.append(sender_snippet)
            except Exception:
                result_lines.append(sender_snippet)
        else:
            result_lines.append(f"{sender_file} [project: {sender_project}]")

        # Add connection indicator
        result_lines.append(f"[{technology}] Connection Connected with")

        # Add receiver info with code snippet
        if receiver_snippet and receiver_lines:
            result_lines.append(f"{receiver_file} [project: {receiver_project}]")
            try:
                import json
                # Handle different input formats for lines_data
                if isinstance(receiver_lines, str) and receiver_lines.strip():
                    lines_data = json.loads(receiver_lines)
                elif isinstance(receiver_lines, list):
                    lines_data = receiver_lines
                else:
                    lines_data = None

                if isinstance(lines_data, list) and len(lines_data) >= 1:
                    start_line = lines_data[0]
                    snippet_lines = receiver_snippet.split('\n')
                    for i, line in enumerate(snippet_lines):
                        result_lines.append(f"{start_line + i} | {line}")
                else:
                    result_lines.append(receiver_snippet)
            except Exception:
                result_lines.append(receiver_snippet)
        else:
            result_lines.append(f"{receiver_file} [project: {receiver_project}]")

        result_lines.append("")  # Empty line between mappings

    return result_lines


def _format_grouped_connections(technology: str, connections: List[Dict[str, Any]], direction: str) -> List[str]:
    """
    Format multiple connections of the same technology with detailed code snippets.

    Args:
        technology: Technology name (e.g., 'HTTP/REST')
        connections: List of connections using this technology
        direction: "incoming" or "outgoing"

    Returns:
        List of formatted connection strings with code snippets
    """
    if not connections:
        return []

    result_lines = []

    for i, conn in enumerate(connections):
        # Get file and project info based on direction
        if direction == "incoming":
            file_path = conn.get('source_file_path', conn.get('connected_file_path', 'unknown'))
            project_name = conn.get('source_project_name', conn.get('connected_project_name', 'unknown'))
        else:
            file_path = conn.get('target_file_path', conn.get('connected_file_path', 'unknown'))
            project_name = conn.get('target_project_name', conn.get('connected_project_name', 'unknown'))

        # Add file header
        result_lines.append(f"{file_path} [project: {project_name}]")

        # Add code snippet with line numbers if available
        code_snippet = conn.get('code_snippet', '')
        snippet_lines = conn.get('snippet_lines', '')

        if code_snippet and snippet_lines:
            try:
                import json
                # Handle different input formats for lines_data
                if isinstance(snippet_lines, str) and snippet_lines.strip():
                    lines_data = json.loads(snippet_lines)
                elif isinstance(snippet_lines, list):
                    lines_data = snippet_lines
                else:
                    lines_data = None

                if isinstance(lines_data, list) and len(lines_data) >= 1:
                    start_line = lines_data[0]
                    snippet_code_lines = code_snippet.split('\n')
                    for j, line in enumerate(snippet_code_lines):
                        result_lines.append(f"{start_line + j} | {line}")
                else:
                    # Fallback: show code without line numbers
                    for line in code_snippet.split('\n'):
                        result_lines.append(f"   {line}")
            except Exception:
                # Fallback: show code without line numbers
                for line in code_snippet.split('\n'):
                    result_lines.append(f"   {line}")

        # Add technology info
        tech_name = conn.get('technology_name', technology)
        result_lines.append(f"[{tech_name}] Connection Connected with")

        # Add spacing between connections
        if i < len(connections) - 1:
            result_lines.append("")

    return result_lines
