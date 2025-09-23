"""
Formatting utility functions for beautifying node results and output.
"""

import json

from loguru import logger


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

    # Only show block info for GET_BLOCK_DETAILS results
    if node.get("type") and node.get("block_id"):  # Block details result
        block_id = node.get("block_id")
        result_parts.append(f"block_id: {block_id}")
        block_type = node.get("type")
        block_name = node.get("name")
        if block_type:
            result_parts.append(f"block_type: {block_type}")
        if block_name:
            result_parts.append(f"block_name: {block_name}")

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

    # Add connection mappings information if available
    connection_mappings = node.get("connection_mappings", [])

    if connection_mappings:
        result_parts.append("\nconnections:")
        result_parts.append("")

        # Group mappings by sender (source) to handle 1-to-many relationships
        sender_groups = {}
        for mapping in connection_mappings:
            sender_key = (
                mapping.get("sender_file_path", "unknown"),
                mapping.get("sender_code_snippet", ""),
                mapping.get("sender_snippet_lines", ""),
                mapping.get("sender_project", "unknown project"),
            )
            if sender_key not in sender_groups:
                sender_groups[sender_key] = []
            sender_groups[sender_key].append(mapping)

        group_num = 1
        for sender_key, mappings in sender_groups.items():
            (
                sender_file_path,
                sender_code_snippet,
                sender_snippet_lines,
                sender_project,
            ) = sender_key

            sender_project = mappings[0].get("sender_project", "unknown project")
            result_parts.append(
                f"{group_num}. {sender_file_path} [project: {sender_project}]"
            )

            # Add sender code snippet with line numbers (only once per group)
            if sender_code_snippet and sender_code_snippet.strip():
                sender_lines = []
                try:
                    if sender_snippet_lines:
                        sender_lines = json.loads(sender_snippet_lines)
                except BaseException:
                    pass

                code_lines = sender_code_snippet.strip().split("\n")
                for j, line in enumerate(code_lines):
                    if j < len(sender_lines):
                        result_parts.append(f"   {sender_lines[j]:4d} | {line}")
                    else:
                        result_parts.append(f"      | {line}")

            # Add single arrow with technology name for the group
            technology_name = mappings[0].get("technology_name", "unknown")
            result_parts.append("")
            result_parts.append(f"    [{technology_name}] Connection Connected with")
            result_parts.append("")

            # Add all targets for this sender
            for i, mapping in enumerate(mappings):
                receiver_file_path = mapping.get("receiver_file_path", "unknown")
                receiver_code_snippet = mapping.get("receiver_code_snippet", "")
                receiver_snippet_lines = mapping.get("receiver_snippet_lines", "")

                receiver_project = mapping.get("receiver_project", "unknown project")
                result_parts.append(
                    f"   {receiver_file_path} [project: {receiver_project}]"
                )

                # Add receiver code snippet with line numbers
                if receiver_code_snippet and receiver_code_snippet.strip():
                    receiver_lines = []
                    try:
                        if receiver_snippet_lines:
                            receiver_lines = json.loads(receiver_snippet_lines)
                    except BaseException:
                        pass

                    code_lines = receiver_code_snippet.strip().split("\n")
                    for j, line in enumerate(code_lines):
                        if j < len(receiver_lines):
                            result_parts.append(f"   {receiver_lines[j]:4d} | {line}")
                        else:
                            result_parts.append(f"      | {line}")

                # Add spacing between targets (but not after the last one in a group)
                if i < len(mappings) - 1:
                    result_parts.append("")

            # Add spacing between sender groups
            if group_num < len(sender_groups):
                result_parts.append("")

            group_num += 1

    return "\n".join(result_parts)


def beautify_node_result_metadata_only(node, idx=None, total_nodes=None):
    """
    Format node result with only essential metadata (no code content).

    Args:
        node: Node data dictionary
        idx: Node index number
        total_nodes: Total number of nodes being sent (for guidance)
    """

    logger.debug("Node: {}", node)
    # Handle dependency scope single-node formatting
    dependency_scope = node.get("dependency_scope")
    if dependency_scope:
        scope = dependency_scope
        anchor = scope.get("anchor_file_path", "unknown")
        error = scope.get("error")
        imports = scope.get("imports", []) or []
        importers = scope.get("importers", []) or []
        chains = scope.get("dependency_chain", []) or []
        impacts = scope.get("connection_impacts", []) or []
        max_depth = scope.get("max_depth")

        out = []
        out.append(f"FILE: {anchor}")
        if error:
            out.append("")
            out.append(f"ERROR: {error}")

        if imports:
            out.append("")
            out.append(f"Imports ({len(imports)})")
            for i, row in enumerate(imports, 1):
                fp = row.get("file_path", "?")
                lang = row.get("language", "?")
                proj = row.get("project_name", "?")
                imp = row.get("import_content", "")
                out.append(f"{i}) {anchor} -> {fp} [lang={lang}; proj={proj}]")
                if imp:
                    out.append(f"   import: {imp}")

        if importers:
            out.append("")
            out.append(f"Imported By ({len(importers)})")
            for i, row in enumerate(importers, 1):
                fp = row.get("file_path", "?")
                lang = row.get("language", "?")
                proj = row.get("project_name", "?")
                imp = row.get("import_content", "")
                out.append(f"{i}) {fp} -> {anchor} [lang={lang}; proj={proj}]")
                if imp:
                    out.append(f"   import: {imp}")

        if chains:
            out.append("")
            chains_count = len(chains)
            if max_depth is not None:
                out.append(
                    f"Dependency Chain (max_depth={max_depth}, chains={chains_count})"
                )
            else:
                out.append(f"Dependency Chain (chains={chains_count})")
            for i, row in enumerate(chains, 1):
                path = row.get("path") or ""
                out.append(f"{i}) {path}")

        if impacts:
            out.append("")
            out.append(f"Connection Impact ({len(impacts)})")
            for i, imp in enumerate(impacts, 1):
                other = imp.get("other_file", "?")
                tech_name = imp.get("technology_name", "?")
                itype = imp.get("impact_type", "?")
                conf = imp.get("match_confidence")
                desc = imp.get("description", "")
                conf_str = (
                    f"{int(conf)}%" if isinstance(conf, (int, float)) else str(conf)
                )
                out.append(
                    f"{i}) {anchor} => {other} [tech={tech_name}; impact={itype}; conf={conf_str}]"
                )
                if desc:
                    out.append(f"   desc: {desc}")

                def _num_snip(code_snippet, lines_json):
                    try:
                        if isinstance(lines_json, str):
                            lines = json.loads(lines_json) if lines_json else []
                        else:
                            lines = lines_json or []
                        if not isinstance(lines, list):
                            lines = []
                    except Exception:
                        lines = []
                    snippet = (code_snippet or "").rstrip("\n")
                    if not snippet:
                        return ""
                    code_lines = snippet.split("\n")
                    parts = []
                    n = min(len(lines), len(code_lines))
                    for j in range(n):
                        parts.append(f"L{lines[j]}: {code_lines[j]}")
                    for j in range(n, len(code_lines)):
                        parts.append(code_lines[j])
                    return "\n".join(parts)

                a_snip = _num_snip(
                    imp.get("anchor_code_snippet", ""), imp.get("anchor_snippet_lines")
                )
                if a_snip:
                    out.append("   code@anchor:")
                    out.extend([f"     {line}" for line in a_snip.split("\n")])

                o_snip = _num_snip(
                    imp.get("other_code_snippet", ""), imp.get("other_snippet_lines")
                )
                if o_snip:
                    out.append("   code@other:")
                    out.extend([f"     {line}" for line in o_snip.split("\n")])

        return "\n".join(out)

    # Fall through to default metadata formatting
    start_line = node.get("start_line")
    end_line = node.get("end_line")
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

    # Only show block info for actual blocks
    block_id = node.get("block_id") or node.get("id")
    if block_id:
        block_type = node.get("type", "unknown")
        block_name = node.get("name", "unnamed")
    else:
        block_type = "file"
        block_name = "unknown"

    # Calculate tree position for hierarchy display
    hierarchy_path = node.get("hierarchy_path", [])
    parent_block_id = node.get("parent_block_id")

    # Determine tree symbols based on hierarchy
    if parent_block_id is None:
        # Root level block
        if idx == 1:
            tree_symbol = "" if total_nodes == 1 else "├─ "
        elif idx == total_nodes:
            tree_symbol = "└─ "
        else:
            tree_symbol = "├─ "
        indent = ""
    else:
        # Child block - determine depth from hierarchy path
        depth = len(hierarchy_path) if hierarchy_path else 1
        indent = "│  " * (depth - 1)

        # For now, assume it's the last child (in real implementation,
        # we'd need parent-child relationship info)
        tree_symbol = "└─ "

    # Build tree-style representation
    tree_line = f"{indent}{tree_symbol}{block_type}: {block_name} (lines {start_end_str}) [block_id={block_id}]"

    # If this is the first node, add a header
    if idx == 1:
        file_path = node.get("file_path", "unknown")
        result_parts = [
            f"File: {file_path}",
            f"Total blocks: {total_nodes}",
            "",
            "File Structure:",
            tree_line,
        ]
    else:
        result_parts = [tree_line]

    return "\n".join(result_parts)
