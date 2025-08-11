"""
Utilities for formatting and beautifying enriched context data from graph operations.

This module provides functions to format the rich context data returned by
GraphOperations.get_enriched_block_context() and GraphOperations.get_enriched_file_context()
into human-readable, structured text for display in search results and agent responses.
"""

import json
from typing import Dict, Any, List, Optional
from tools.utils.code_processing_utils import add_line_numbers_to_code


def beautify_enriched_block_context(
    enriched_context: Dict[str, Any],
    index: int = 1,
    total_nodes: int = 1,
    include_code: bool = True,
    max_code_lines: Optional[int] = None
) -> str:
    """
    Format enriched block context into a beautiful, readable string.

    Args:
        enriched_context: Result from GraphOperations.get_enriched_block_context()
        index: Position in search results
        total_nodes: Total number of results
        include_code: Whether to include code content
        max_code_lines: Maximum lines of code to display

    Returns:
        Formatted string representation
    """
    if not enriched_context:
        return f"❌ Node {index}/{total_nodes}: No context available"

    block = enriched_context.get('block', {})
    file_context = enriched_context.get('file_context', {})
    connection_summary = enriched_context.get('connection_summary', {})
    parent_block = enriched_context.get('parent_block')
    child_blocks = enriched_context.get('child_blocks', [])

    # Header
    result_parts = []
    result_parts.append(f"🎯 Result {index}/{total_nodes}")
    result_parts.append("=" * 60)

    # Block information
    block_type = block.get('type', 'unknown').title()
    block_name = block.get('name', 'unnamed')
    result_parts.append(f"📦 **{block_type}**: `{block_name}`")

    # File context
    file_path = file_context.get('file_path', 'unknown')
    language = file_context.get('language', 'unknown')
    project_name = file_context.get('project_name', 'unknown')
    result_parts.append(f"📁 **File**: {file_path}")
    result_parts.append(f"🏷️  **Language**: {language} | **Project**: {project_name}")

    # Line information
    start_line = block.get('start_line')
    end_line = block.get('end_line')
    if start_line and end_line:
        line_count = end_line - start_line + 1
        result_parts.append(f"📏 **Lines**: {start_line}-{end_line} ({line_count} lines)")

    # Hierarchy information
    if parent_block:
        parent_name = parent_block.get('name', 'unnamed')
        parent_type = parent_block.get('type', 'unknown')
        result_parts.append(f"⬆️  **Parent**: {parent_type} `{parent_name}`")

    if child_blocks:
        child_count = len(child_blocks)
        child_names = [f"`{child.get('name', 'unnamed')}`" for child in child_blocks[:3]]
        child_summary = ", ".join(child_names)
        if child_count > 3:
            child_summary += f" ... (+{child_count - 3} more)"
        result_parts.append(f"⬇️  **Children** ({child_count}): {child_summary}")

    # Connection details
    connections = enriched_context.get('connections', {})
    if connections:
        incoming_conns = connections.get('incoming', [])
        outgoing_conns = connections.get('outgoing', [])

        if incoming_conns or outgoing_conns:
            result_parts.append(f"🔗 **Connections**: {len(incoming_conns)} incoming | {len(outgoing_conns)} outgoing")

            # Show detailed incoming connections grouped by technology
            if incoming_conns:
                result_parts.append("📥 **Incoming connections**:")
                grouped_incoming = _group_connections_by_technology(incoming_conns, "incoming")
                tech_count = 0
                for technology, tech_connections in grouped_incoming.items():
                    if tech_count >= 3:  # Limit to 3 technology groups
                        remaining_techs = len(grouped_incoming) - tech_count
                        result_parts.append(f"   ... and {remaining_techs} more technologies")
                        break
                    conn_info = _format_grouped_connections(technology, tech_connections, "incoming")
                    if conn_info:
                        result_parts.append(f"   • {conn_info}")
                    tech_count += 1

            # Show detailed outgoing connections grouped by technology
            if outgoing_conns:
                result_parts.append("📤 **Outgoing connections**:")
                grouped_outgoing = _group_connections_by_technology(outgoing_conns, "outgoing")
                tech_count = 0
                for technology, tech_connections in grouped_outgoing.items():
                    if tech_count >= 3:  # Limit to 3 technology groups
                        remaining_techs = len(grouped_outgoing) - tech_count
                        result_parts.append(f"   ... and {remaining_techs} more technologies")
                        break
                    conn_info = _format_grouped_connections(technology, tech_connections, "outgoing")
                    if conn_info:
                        result_parts.append(f"   • {conn_info}")
                    tech_count += 1

    # Code content
    if include_code and block.get('content'):
        result_parts.append("")
        result_parts.append("💻 **Code**:")
        result_parts.append("-" * 40)

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
    include_code: bool = False,
    max_code_lines: Optional[int] = 50
) -> str:
    """
    Format enriched file context into a beautiful, readable string.

    Args:
        enriched_context: Result from GraphOperations.get_enriched_file_context()
        index: Position in search results
        total_nodes: Total number of results
        include_code: Whether to include file content
        max_code_lines: Maximum lines of code to display

    Returns:
        Formatted string representation
    """
    if not enriched_context:
        return f"❌ Node {index}/{total_nodes}: No context available"

    file_data = enriched_context.get('file', {})
    blocks_summary = enriched_context.get('blocks_summary', {})
    connection_summary = enriched_context.get('connection_summary', {})
    imports = enriched_context.get('imports', [])
    importers = enriched_context.get('importers', [])
    dependency_context = enriched_context.get('dependency_context', {})

    # Header
    result_parts = []
    result_parts.append(f"📄 File Result {index}/{total_nodes}")
    result_parts.append("=" * 60)

    # File information
    file_path = file_data.get('file_path', 'unknown')
    language = file_data.get('language', 'unknown')
    project_name = file_data.get('project_name', 'unknown')
    result_parts.append(f"📁 **File**: {file_path}")
    result_parts.append(f"🏷️  **Language**: {language} | **Project**: {project_name}")

    # Block summary
    if blocks_summary:
        block_count = blocks_summary.get('total_blocks', 0)
        if block_count > 0:
            block_types = blocks_summary.get('block_types', [])
            types_summary = ", ".join([f"{bt.get('type', 'unknown')} ({bt.get('count', 0)})"
                                     for bt in block_types[:3]])
            if len(block_types) > 3:
                types_summary += f" ... (+{len(block_types) - 3} more types)"
            result_parts.append(f"📦 **Blocks** ({block_count}): {types_summary}")

    # Dependency information
    if dependency_context:
        dep_parts = []
        imports_count = dependency_context.get('imports_count', 0)
        importers_count = dependency_context.get('importers_count', 0)

        if imports_count > 0:
            dep_parts.append(f"📥 imports {imports_count}")
        if importers_count > 0:
            dep_parts.append(f"📤 imported by {importers_count}")

        if dep_parts:
            result_parts.append(f"🔗 **Dependencies**: {' | '.join(dep_parts)}")

    # Connection details
    connections = enriched_context.get('connections', {})
    if connections:
        incoming_conns = connections.get('incoming', [])
        outgoing_conns = connections.get('outgoing', [])

        if incoming_conns or outgoing_conns:
            result_parts.append(f"🔗 **Connections**: {len(incoming_conns)} incoming | {len(outgoing_conns)} outgoing")

            # Show detailed incoming connections grouped by technology
            if incoming_conns:
                result_parts.append("📥 **Incoming connections**:")
                grouped_incoming = _group_connections_by_technology(incoming_conns, "incoming")
                tech_count = 0
                for technology, tech_connections in grouped_incoming.items():
                    if tech_count >= 4:  # Show more for files
                        remaining_techs = len(grouped_incoming) - tech_count
                        result_parts.append(f"   ... and {remaining_techs} more technologies")
                        break
                    conn_info = _format_grouped_connections(technology, tech_connections, "incoming")
                    if conn_info:
                        result_parts.append(f"   • {conn_info}")
                    tech_count += 1

            # Show detailed outgoing connections grouped by technology
            if outgoing_conns:
                result_parts.append("📤 **Outgoing connections**:")
                grouped_outgoing = _group_connections_by_technology(outgoing_conns, "outgoing")
                tech_count = 0
                for technology, tech_connections in grouped_outgoing.items():
                    if tech_count >= 4:  # Show more for files
                        remaining_techs = len(grouped_outgoing) - tech_count
                        result_parts.append(f"   ... and {remaining_techs} more technologies")
                        break
                    conn_info = _format_grouped_connections(technology, tech_connections, "outgoing")
                    if conn_info:
                        result_parts.append(f"   • {conn_info}")
                    tech_count += 1

    # Import details (top 5)
    if imports:
        import_names = [imp.get('imported_symbol', 'unknown') for imp in imports[:5]]
        import_summary = ", ".join(f"`{name}`" for name in import_names)
        if len(imports) > 5:
            import_summary += f" ... (+{len(imports) - 5} more)"
        result_parts.append(f"📥 **Top Imports**: {import_summary}")

    # File content (if requested)
    if include_code and file_data.get('content'):
        result_parts.append("")
        result_parts.append("💻 **File Content**:")
        result_parts.append("-" * 40)

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
    max_code_lines: Optional[int] = None
) -> str:
    """
    Automatically determine whether to format as block or file context.

    Args:
        enriched_context: Result from GraphOperations enriched context functions
        index: Position in search results
        total_nodes: Total number of results
        include_code: Whether to include code content
        max_code_lines: Maximum lines of code to display

    Returns:
        Formatted string representation
    """
    if not enriched_context:
        return f"❌ Node {index}/{total_nodes}: No context available"

    # Determine type based on presence of 'block' or 'file' key
    if 'block' in enriched_context:
        return beautify_enriched_block_context(
            enriched_context, index, total_nodes, include_code, max_code_lines
        )
    elif 'file' in enriched_context:
        return beautify_enriched_file_context(
            enriched_context, index, total_nodes, include_code, max_code_lines
        )
    else:
        return f"❌ Node {index}/{total_nodes}: Unknown context type"


def format_chunk_with_enriched_context(
    enriched_context: Dict[str, Any],
    chunk_start_line: int,
    chunk_end_line: int,
    chunk_code: str,
    index: int = 1,
    total_nodes: int = 1
) -> str:
    """
    Format enriched context with specific chunk information highlighted.

    Args:
        enriched_context: Result from GraphOperations enriched context functions
        chunk_start_line: Start line of the chunk
        chunk_end_line: End line of the chunk
        chunk_code: The specific chunk code content
        index: Position in search results
        total_nodes: Total number of results

    Returns:
        Formatted string with chunk information highlighted
    """
    if not enriched_context:
        return f"❌ Chunk {index}/{total_nodes}: No context available"

    # Get base formatting
    base_format = beautify_enriched_context_auto(
        enriched_context, index, total_nodes, include_code=False
    )

    # Add chunk-specific information
    chunk_parts = [base_format]
    chunk_parts.append("")
    chunk_parts.append("🎯 **Chunk Details**:")
    chunk_parts.append("-" * 40)

    line_count = chunk_end_line - chunk_start_line + 1
    chunk_parts.append(f"📏 **Chunk Lines**: {chunk_start_line}-{chunk_end_line} ({line_count} lines)")

    # Add chunk code with line numbers
    chunk_parts.append("")
    chunk_parts.append("💻 **Chunk Code**:")
    chunk_parts.append("-" * 40)
    numbered_chunk = add_line_numbers_to_code(chunk_code, chunk_start_line)
    chunk_parts.append(numbered_chunk)

    return "\n".join(chunk_parts)


def _group_connections_by_technology(connections: List[Dict[str, Any]], direction: str) -> Dict[str, List[Dict[str, Any]]]:
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

def _format_grouped_connections(technology: str, connections: List[Dict[str, Any]], direction: str) -> str:
    """
    Format multiple connections of the same technology showing all sources/targets.

    Args:
        technology: Technology name (e.g., 'HTTP/REST')
        connections: List of connections using this technology
        direction: "incoming" or "outgoing"

    Returns:
        Formatted string showing all files using this technology
    """
    if not connections:
        return ""

    # Get unique files and projects
    files_info = []
    connection_types = set()
    confidences = []
    projects = set()

    for conn in connections:
        # Get file and project info based on direction
        if direction == "incoming":
            file_path = conn.get('source_file_path', conn.get('connected_file_path', 'unknown'))
            project_name = conn.get('source_project_name', conn.get('connected_project_name', 'unknown'))
        else:
            file_path = conn.get('target_file_path', conn.get('connected_file_path', 'unknown'))
            project_name = conn.get('target_project_name', conn.get('connected_project_name', 'unknown'))

        # Shorten file path if needed
        if file_path and file_path != 'unknown':
            if len(file_path) > 40:
                display_file = file_path.split('/')[-1]
            else:
                display_file = file_path
            files_info.append(display_file)

        if project_name and project_name != 'unknown':
            projects.add(project_name)

        if conn.get('connection_type'):
            connection_types.add(conn.get('connection_type'))

        if conn.get('match_confidence'):
            confidences.append(conn.get('match_confidence'))

    # Build the formatted string
    parts = [f"`{technology}`"]

    # Add direction indicator and files
    if direction == "incoming":
        parts.append("from")
    else:
        parts.append("to")

    # Format file list
    unique_files = list(set(files_info))
    if len(unique_files) == 1:
        parts.append(f"**{unique_files[0]}**")
    elif len(unique_files) <= 3:
        file_list = ", ".join(f"**{f}**" for f in unique_files)
        parts.append(file_list)
    else:
        first_three = ", ".join(f"**{f}**" for f in unique_files[:3])
        parts.append(f"{first_three} (+{len(unique_files)-3} more)")

    # Add project info if unified
    if len(projects) == 1:
        parts.append(f"(project: {list(projects)[0]})")
    elif len(projects) > 1:
        parts.append(f"({len(projects)} projects)")

    # Add connection type if unified
    if len(connection_types) == 1:
        parts.append(f"[{list(connection_types)[0]}]")
    elif len(connection_types) > 1:
        parts.append(f"[{len(connection_types)} types]")

    # Add confidence range if available
    if confidences:
        if len(confidences) == 1:
            parts.append(f"({confidences[0]:.1%} confidence)")
        else:
            min_conf = min(confidences)
            max_conf = max(confidences)
            parts.append(f"({min_conf:.1%}-{max_conf:.1%} confidence)")

    return " ".join(parts)

def _format_connection_detail(connection: Dict[str, Any], direction: str) -> str:
    """
    Format a single connection with detailed information.
    (Kept for backward compatibility)
    """
    if not connection:
        return ""

    # Get connection details
    technology = connection.get('technology_name', 'unknown')
    description = connection.get('description', 'No description')
    connection_type = connection.get('connection_type', '')
    confidence = connection.get('match_confidence', 0)

    # Get connected file and project info based on direction
    if direction == "incoming":
        file_path = connection.get('source_file_path', connection.get('connected_file_path', 'unknown'))
        project_name = connection.get('source_project_name', connection.get('connected_project_name', 'unknown'))
        project_id = connection.get('source_project_id', connection.get('connected_project_id', ''))
    else:
        file_path = connection.get('target_file_path', connection.get('connected_file_path', 'unknown'))
        project_name = connection.get('target_project_name', connection.get('connected_project_name', 'unknown'))
        project_id = connection.get('target_project_id', connection.get('connected_project_id', ''))

    # Format the connection info
    parts = []

    # Add technology if available
    if technology and technology != 'unknown':
        parts.append(f"`{technology}`")

    # Add file path (shortened)
    if file_path and file_path != 'unknown':
        if len(file_path) > 40:
            filename = file_path.split('/')[-1]
            parts.append(f"**{filename}**")
        else:
            parts.append(f"**{file_path}**")

    # Add project info
    if project_name and project_name != 'unknown':
        parts.append(f"(project: {project_name})")

    # Add connection type if available
    if connection_type:
        parts.append(f"[{connection_type}]")

    # Add confidence if meaningful
    if confidence and confidence > 0:
        parts.append(f"({confidence:.1%} confidence)")

    result = " ".join(parts) if parts else description[:50]

    # Fallback to description if no other info
    if not result or result.strip() == "":
        result = description[:60] + ("..." if len(description) > 60 else "")

    return result
