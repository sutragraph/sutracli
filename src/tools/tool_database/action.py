from loguru import logger
from typing import Iterator, Dict, Any, List
from graph.graph_operations import GraphOperations
import subprocess
from tools.utils import (
    beautify_node_result,
    chunk_large_code_clean,
)
from queries.agent_queries import (
    GET_FILE_BY_ID,
    GET_FILE_BLOCK_SUMMARY,
    GET_DEPENDENCY_CHAIN,
)
from tools.utils.formatting_utils import (
    beautify_node_result_metadata_only,
)
from pathlib import Path
import os
import json
from models.agent import AgentAction
from tools.utils.constants import (
    DATABASE_QUERY_CONFIG,
    SEARCH_CONFIG,
)
from tools.delivery_actions import (
    check_pending_delivery,
    register_delivery_queue_and_get_first_batch_with_line_limit,
)


def should_chunk_content(code_content: str, chunking_threshold: int) -> bool:
    """
    Determine if content should be chunked.

    Args:
        code_content: Code content to check
        chunking_threshold: Threshold for chunking

    Returns:
        True if content should be chunked
    """
    code_lines = code_content.split("\n")
    return len(code_lines) > chunking_threshold


def create_chunk_info(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized chunk info dictionary.

    Args:
        chunk: Chunk data from chunk_large_code_clean

    Returns:
        Standardized chunk info dictionary
    """
    return {
        "chunk_num": chunk.get("chunk_num", 1),
        "total_chunks": chunk.get("total_chunks", 1),
        "start_line": chunk.get("start_line", 1),
        "end_line": chunk.get("end_line", 1),
        "total_lines": chunk.get("total_lines", 0),
        "original_file_lines": chunk.get("original_file_lines", 0),
    }


def execute_structured_database_query(
    action: AgentAction, context: str = "agent"
) -> Iterator[Dict[str, Any]]:
    # Initialize variables for exception handling
    query_name = action.parameters.get("query_name", "unknown")
    code_snippet = action.parameters.get("code_snippet", True)

    try:
        # Get graph operations instance
        graph_ops = GraphOperations()

        query_params = {
            k: v
            for k, v in action.parameters.items()
            if k not in ["query_name", "code_snippet", "fetch_next_chunk"]
        }

        logger.debug(f"🗄️ Executing structured query: {query_name}")
        logger.debug(f"📋 Query parameters: {query_params}")

        query_config = {}
        sql_mapping = {
            "GET_FILE_BY_PATH": GET_FILE_BY_ID,
            "GET_FILE_BLOCK_SUMMARY": GET_FILE_BLOCK_SUMMARY,
            "GET_BLOCK_DETAILS": "",
            "GET_DEPENDENCY_CHAIN": GET_DEPENDENCY_CHAIN,
        }

        for query_key, config in DATABASE_QUERY_CONFIG.items():
            if query_key in sql_mapping:
                query_config[query_key] = {
                    "sql": sql_mapping[query_key],
                    "required_params": config["required_params"],
                    "optional_params": config.get("optional_params", []),
                }
        base_query_name = query_name
        include_code = code_snippet

        logger.debug(
            f"{'✅' if include_code else '🚫'} Code snippets {'enabled' if include_code else 'disabled'} for query: {base_query_name}"
        )

        if base_query_name not in query_config:
            error_msg = f"Unknown query: {query_name}"
            logger.error(f"❌ {error_msg}")
            yield {
                "type": "tool_use",
                "tool_name": "database",
                "query_name": base_query_name,
                "query": query_params,
                "error": error_msg,
                "include_code": include_code,
            }
            return
        config = query_config[base_query_name]
        sql_query = config["sql"]
        final_params = {}

        for param in config["required_params"]:
            if param not in query_params:
                error_msg = (
                    f"Missing required parameter '{param}' for query {query_name}"
                )
                logger.error(f"❌ {error_msg}")
                yield {
                    "type": "tool_use",
                    "tool_name": "database",
                    "query_name": base_query_name,
                    "query": query_params,
                    "error": error_msg,
                    "include_code": include_code,
                }
                return

            # Fix file path parameter - prepend current directory if path doesn't start with current dir
            if param == "file_path":
                file_path = query_params[param]
                current_dir = Path.cwd()
                file_path_obj = Path(file_path)

                # If it's already an absolute path, use as is
                if file_path_obj.is_absolute():
                    final_params[param] = str(file_path_obj)
                else:
                    # Check if file path starts with current directory
                    try:
                        # If file_path is relative to current dir, this will work
                        file_path_obj.relative_to(current_dir)
                        # Path is already relative to current dir, use as is
                        final_params[param] = str(file_path_obj)
                    except ValueError:
                        # Path is not relative to current dir, need to fix it

                        # Check if the file path starts with the last component of current_dir
                        # to avoid duplication like server/server/src/index.js
                        current_dir_name = current_dir.name
                        file_path_parts = Path(file_path).parts

                        if file_path_parts and file_path_parts[0] == current_dir_name:
                            # The file path already starts with the current directory name
                            # Try to construct path by going up one level and then adding the file path
                            parent_dir = current_dir.parent
                            fixed_path = parent_dir / file_path
                            final_params[param] = str(fixed_path)
                            logger.debug(
                                f"🔧 Fixed file path (avoiding duplication): {query_params[param]} -> {fixed_path}"
                            )
                        else:
                            # Normal case: concatenate with current dir
                            fixed_path = current_dir / file_path
                            final_params[param] = str(fixed_path)
                            logger.debug(
                                f"🔧 Fixed file path: {query_params[param]} -> {fixed_path}"
                            )
            else:
                final_params[param] = query_params[param]

        optional_params = config.get("optional_params", [])
        for param in optional_params:
            if param in query_params:
                # Convert line number parameters to integers
                if (
                    param in ["start_line", "end_line"]
                    and query_params[param] is not None
                ):
                    try:
                        final_params[param] = int(query_params[param])
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid {param} value: {query_params[param]}, setting to None"
                        )
                        final_params[param] = None
                else:
                    final_params[param] = query_params[param]
            else:
                final_params[param] = None

        final_params["project_id"] = None
        logger.debug(f"🎭 Final parameters: {final_params}")
        logger.debug(f"📋 Required params: {config['required_params']}")

        # Execute query using graph_operations
        if base_query_name == "GET_FILE_BY_PATH":
            # Special handling for GET_FILE_BY_PATH - convert file_path to file_id and use GET_FILE_BY_ID
            logger.debug(f"🔍 TRACE PATH: *** GET_FILE_BY_PATH EXECUTION ***")
            file_path = final_params.get("file_path")
            logger.debug(f"🔍 TRACE: GET_FILE_BY_PATH for file_path: {file_path}")
            if file_path:
                file_id = graph_ops._get_file_id_by_path(file_path)
                logger.debug(f"🔍 TRACE: Found file_id: {file_id}")
                if file_id:
                    results = graph_ops.connection.execute_query(sql_query, (file_id,))
                    logger.debug(
                        f"🔍 TRACE: Database query returned {len(results) if results else 0} results"
                    )

                    # Apply line range filtering if start_line and end_line are provided
                    start_line = final_params.get("start_line")
                    end_line = final_params.get("end_line")
                    if results and (start_line is not None or end_line is not None):
                        for i, result in enumerate(results):
                            result_dict = dict(result) if hasattr(result, 'keys') else result
                            content = result_dict.get('content', '')
                            if content:
                                content_lines = content.split('\n')
                                total_lines = len(content_lines)

                                # Default to full range if not specified
                                start_idx = (start_line - 1) if start_line is not None else 0
                                end_idx = end_line if end_line is not None else total_lines

                                # Ensure indices are within bounds
                                start_idx = max(0, min(start_idx, total_lines - 1))
                                end_idx = max(start_idx + 1, min(end_idx, total_lines))

                                # Filter content to specified line range
                                filtered_lines = content_lines[start_idx:end_idx]
                                filtered_content = '\n'.join(filtered_lines)

                                # Update the result with filtered content and line info
                                if isinstance(result, dict):
                                    result['content'] = filtered_content
                                    result['start_line'] = start_line if start_line is not None else 1
                                    result['end_line'] = end_line if end_line is not None else total_lines
                                    result['lines'] = [result['start_line'], result['end_line']]
                                    # Remove block-related fields for GET_FILE_BY_PATH
                                    result.pop('id', None)
                                    result.pop('block_id', None)
                                else:
                                    # Convert to dict if it's not already
                                    result_dict['content'] = filtered_content
                                    result_dict['start_line'] = start_line if start_line is not None else 1
                                    result_dict['end_line'] = end_line if end_line is not None else total_lines
                                    result_dict['lines'] = [result_dict['start_line'], result_dict['end_line']]
                                    # Remove block-related fields for GET_FILE_BY_PATH
                                    result_dict.pop('id', None)
                                    result_dict.pop('block_id', None)
                                    results[i] = result_dict

                                logger.debug(f"🔍 TRACE: Filtered content from lines {start_idx + 1}-{end_idx} ({len(filtered_lines)} lines)")

                    # Get connection mappings for the file/line range if we have results
                    if results:
                        connection_mappings = graph_ops._get_connection_mappings_for_display(
                            file_id, start_line, end_line
                        )
                        logger.debug(f"🔗 CONNECTIONS: Retrieved connection mappings for file_id {file_id}, lines {start_line}-{end_line}")
                        logger.debug(f"🔗 CONNECTIONS: Found {len(connection_mappings)} connection mappings")
                        if connection_mappings:
                            result_dict = dict(results[0]) if hasattr(results[0], 'keys') else results[0]
                            result_dict['connection_mappings'] = connection_mappings
                            results[0] = result_dict
                            logger.debug(f"🔗 CONNECTIONS: Added connection mappings to result_dict")
                else:
                    results = []
                    logger.debug("🔍 TRACE: No file_id found, empty results")
            else:
                results = []
                logger.debug(f"🔍 TRACE: No file_path provided, empty results")
        else:
            # For other queries, convert dict params to tuple based on query requirements
            if base_query_name == "GET_FILE_BLOCK_SUMMARY":
                file_path = final_params.get("file_path")
                if file_path:
                    file_id = graph_ops._get_file_id_by_path(file_path)
                    summary = (
                        graph_ops.get_file_block_summary(file_id)
                        if file_id
                        else []
                    )

                    results = summary
                    # Route through metadata-only pipeline to get tree-style output
                    include_code = False

            elif base_query_name == "GET_DEPENDENCY_CHAIN":
                file_path = final_params.get("file_path")
                depth = int(final_params.get("depth", 5))
                file_id = None

                if file_path:
                    file_id = graph_ops._get_file_id_by_path(file_path)

                if not file_path or not file_id:
                    error_msg = "No file path provided. Please specify a file path to analyze dependencies." if not file_path else "File not found in database."
                    results = [{
                        "file_path": file_path,
                        "dependency_scope": {
                            "anchor_file_path": file_path or "unknown",
                            "error": error_msg,
                            "imports": [],
                            "importers": [],
                            "dependency_chain": [],
                            "connection_impacts": [],
                            "max_depth": depth
                        }
                    }]
                else:
                    scope = graph_ops.get_search_scope_by_import_graph(file_id, "both", depth)
                    results = [{"file_path": scope.get("anchor_file_path", "unknown"), "dependency_scope": scope}]
                include_code = False

            elif base_query_name == "GET_BLOCK_DETAILS":
                block_id = final_params.get("block_id")
                if not block_id:
                    return []
                block_details = graph_ops.get_block_details(block_id)
                if block_details:
                    results = [block_details]
                else:
                    results = []
            else:
                results = []
        logger.debug(f"📊 Query returned {len(results)} results")

        if not results:
            # For GET_FILE_BY_PATH, try ripgrep fallback to find similar file names
            if base_query_name == "GET_FILE_BY_PATH" and "file_path" in final_params:
                file_path = final_params["file_path"]
                filename = os.path.basename(file_path)
                logger.debug("Trying ripgrep fallback for file: %s", filename)

                # Use ripgrep to search for the filename
                try:
                    cmd = ["rg", "-l", "--fixed-strings", filename]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, cwd="."
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        found_files = result.stdout.strip().split("\n")
                        logger.debug(f"Ripgrep found {len(found_files)} files with similar names")
                        # Try to get file_id for the first found file
                        for found_file in found_files[:3]:  # Try first 3 matches
                            file_id = graph_ops._get_file_id_by_path(found_file)
                            if file_id:
                                results = graph_ops.connection.execute_query(
                                    sql_query, (file_id,)
                                )
                                if results:
                                    logger.debug(f"Found file data using ripgrep match: {found_file}")
                                    break
                    else:
                        logger.debug("Ripgrep fallback found no matching files")
                except Exception as e:
                    logger.debug(f"Ripgrep fallback failed: {e}")

            if not results:
                yield {
                    "type": "tool_use",
                    "tool_name": "database",
                    "query_name": query_name,
                    "query": final_params,
                    "result": "result found: 0",
                    "data": "",
                    "include_code": include_code,
                    "total_nodes": 0,
                }
                return

        total_nodes = len(results)

        # Handle different scenarios based on include_code and number of results
        if not include_code:
            # Process metadata-only results in batches
            batch_size = 30  # Default batch size for metadata
            batches = [results[i : i + batch_size] for i in range(0, len(results), batch_size)]

            for batch_num, batch in enumerate(batches, 1):
                # Process metadata-only results for this batch
                processed_batch = process_metadata_only_results(batch, len(batch))

                # Extract project information from first item in batch
                project_name = None
                if batch:
                    first_item = batch[0]
                    if hasattr(first_item, "get"):
                        project_name = first_item.get("project_name")
                    elif isinstance(first_item, dict) and "project_name" in first_item:
                        project_name = first_item["project_name"]

                # Ensure processed_batch is a string
                if isinstance(processed_batch, list):
                    processed_batch = "\n".join(str(item) for item in processed_batch)
                elif not isinstance(processed_batch, str):
                    processed_batch = str(processed_batch)

                yield {
                    "type": "tool_use",
                    "tool_name": "database",
                    "query_name": base_query_name,
                    "query": final_params,
                    "data": processed_batch,
                    "include_code": include_code,
                    "result": f"Found {total_nodes} nodes",
                    "current_batch": batch_num,
                    "total_batches": len(batches),
                    "has_more_batches": batch_num < len(batches),
                    "project_name": project_name,}
            return

        elif len(results) == 1:
            logger.debug(f"📊 Processing single result with code content")

            if include_code:
                # Single result with code - check if chunking is needed
                row = results[0]
                result_dict = dict(row) if hasattr(row, "keys") else row
                result_dict = clean_result_dict(result_dict)

                # For GET_FILE_BY_PATH and GET_BLOCK_DETAILS, the content is in 'content' field, for other queries it's in 'code_snippet'
                code_content = result_dict.get(
                    "content", result_dict.get("code_snippet", "")
                )

                if code_content:
                    code_lines = len(code_content.split("\n"))
                else:
                    # Ensure code_snippet field is available for beautify_node_result
                    if (
                        code_content
                        and "content" in result_dict
                        and "code_snippet" not in result_dict
                    ):
                        result_dict["code_snippet"] = code_content

                    # For GET_BLOCK_DETAILS, ensure line information is available
                    if base_query_name == "GET_BLOCK_DETAILS":
                        start_line = result_dict.get("start_line")
                        end_line = result_dict.get("end_line")
                        if start_line is not None and end_line is not None:
                            result_dict["lines"] = [start_line, end_line]

            if code_content:
                # Parse line information
                lines = result_dict.get("lines")
                start_line = None
                if lines:
                    if isinstance(lines, str):
                        try:
                            lines_parsed = json.loads(lines)
                            if (
                                isinstance(lines_parsed, list)
                                and len(lines_parsed) >= 2
                            ):
                                start_line = lines_parsed[0]
                        except Exception:
                            pass
                    elif isinstance(lines, list) and len(lines) >= 2:
                        start_line = lines[0]

                # Note: GET_CODE_FROM_FILE_LINES is no longer supported - removed legacy code
                line_filtered = False

                # DEBUG: Check chunking decision
                code_lines = len(code_content.split("\n"))
                chunking_threshold = SEARCH_CONFIG["chunking_threshold"]
                should_chunk = should_chunk_content(code_content, chunking_threshold)
                logger.debug(
                    f"🔍 TRACE CHUNKING: code_lines={code_lines}, threshold={chunking_threshold}, should_chunk={should_chunk}, line_filtered={line_filtered}"
                )
                logger.debug(f"🔍 TRACE: About to check if chunking is needed...")

                if (
                    should_chunk_content(
                        code_content, SEARCH_CONFIG["chunking_threshold"]
                    )
                    and not line_filtered
                ):
                    # Single result with chunking needed - use delivery manager
                    logger.debug(
                        f"📦 Chunking required for {len(code_content.split('\n'))} lines"
                    )

                    # Check if we have a pending delivery for this query
                    next_item = check_pending_delivery(
                        "database", action.parameters, "database"
                    )
                    if next_item is not None:
                        logger.debug(
                            f"🔍 TRACE CHUNKING: Found pending delivery, returning it"
                        )
                        yield next_item
                        return

                    # No pending delivery - collect all chunks and register them
                    logger.debug("📦 Creating chunks for large file")
                    delivery_items = []
                    chunks = chunk_large_code_clean(
                        code_content,
                        file_start_line=start_line or 1,
                        max_lines=SEARCH_CONFIG["chunk_size"],
                        chunk_threshold=SEARCH_CONFIG["chunking_threshold"],
                    )

                    logger.debug(
                        f"📦 Created {len(chunks)} chunks from {len(code_content.split('\n'))} lines"
                    )

                    for i, chunk in enumerate(chunks):
                        chunked_result = result_dict.copy()
                        # Set the chunk content and remove the original full content
                        chunked_result["code_snippet"] = chunk["content"]
                        if "content" in chunked_result:
                            chunked_result["content"] = chunk["content"]

                        chunk_info = create_chunk_info(chunk)

                        beautified_result = beautify_node_result(
                            chunked_result,
                            1,
                            include_code=True,
                            total_nodes=1,
                            chunk_info=chunk_info,
                        )

                        result_data = beautified_result

                        # Create delivery item
                        delivery_items.append(
                            {
                                "type": "tool_use",
                                "tool_name": "database",
                                "query_name": base_query_name,
                                "query": final_params,
                                "result": "result found: 1",
                                "chunk_info": chunk_info,
                                "data": result_data,
                                "include_code": True,
                                "total_nodes": 1,
                                "chunk_index": chunk["chunk_num"] - 1,
                                "total_items": len(chunks),
                            }
                        )

                    # Register delivery queue and get first batch with line limit for guidance
                    logger.debug(
                        f"📦 Registering {len(delivery_items)} chunk delivery items"
                    )
                    first_item = (
                        register_delivery_queue_and_get_first_batch_with_line_limit(
                            "database",
                            action.parameters,
                            delivery_items,
                            "database",
                        )
                    )
                    if first_item:
                        logger.debug("📦 First chunk delivered successfully")
                        yield first_item
                    else:
                        logger.debug("❌ No first chunk returned")
                    return
                else:
                    # Single result with small code - no chunking needed
                    logger.debug(
                        f"📊 No chunking needed for {len(code_content.split('\n'))} lines"
                    )

                    beautified_result = beautify_node_result(
                        result_dict,
                        1,
                        include_code=True,
                        total_nodes=1,
                    )

                    # Send single batch result for small files
                    result_data = beautified_result

                    logger.debug(
                        f"🔍 TRACE: *** RETURNING SINGLE RESULT (NO CHUNKS) ***"
                    )
                    yield {
                        "type": "tool_use",
                        "tool_name": "database",
                        "query_name": base_query_name,
                        "query": final_params,
                        "result": "result found",
                        "data": result_data,
                        "include_code": include_code,
                        "total_nodes": 1,
                        "project_name": result_dict.get("project_name"),}
                    return
            else:
                # No code content available
                beautified_result = beautify_node_result(
                    result_dict, 1, include_code=True, total_nodes=1
                )

                # Send single batch result for missing code
                result_data = beautified_result

                yield {
                    "type": "tool_use",
                    "tool_name": "database",
                    "query_name": base_query_name,
                    "query": final_params,
                    "result": f"result found",
                    "data": result_data,
                    "include_code": include_code,
                    "total_nodes": 1,
                        "project_name": result_dict.get("project_name"),}
                return

        else:
            # Multiple results with code - use delivery manager for sequential delivery
            # Check if we have a pending delivery for this query
            next_item = check_pending_delivery(
                "database", action.parameters, "database"
            )
            if next_item is not None:
                yield next_item
                return

            # No pending delivery - collect all items and register them
            delivery_items = []

            for i, row in enumerate(results, 1):
                result_dict = dict(row) if hasattr(row, "keys") else row
                result_dict = clean_result_dict(result_dict)

                # For GET_FILE_BY_PATH and GET_BLOCK_DETAILS, the content is in 'content' field, for other queries it's in 'code_snippet'
                code_content = result_dict.get(
                    "content", result_dict.get("code_snippet", "")
                )

                # Ensure code_snippet field is available for beautify_node_result
                if (
                    code_content
                    and "content" in result_dict
                    and "code_snippet" not in result_dict
                ):
                    result_dict["code_snippet"] = code_content

                # For GET_BLOCK_DETAILS, ensure line information is available
                if base_query_name == "GET_BLOCK_DETAILS":
                    start_line = result_dict.get("start_line")
                    end_line = result_dict.get("end_line")
                    if start_line is not None and end_line is not None:
                        result_dict["lines"] = [start_line, end_line]

                if code_content:
                    # Parse line information
                    lines = result_dict.get("lines")
                    start_line = None
                    if lines:
                        if isinstance(lines, str):
                            try:
                                lines_parsed = json.loads(lines)
                                if (
                                    isinstance(lines_parsed, list)
                                    and len(lines_parsed) >= 2
                                ):
                                    start_line = lines_parsed[0]
                            except Exception:
                                pass
                        elif isinstance(lines, list) and len(lines) >= 2:
                            start_line = lines[0]

                    # Note: GET_CODE_FROM_FILE_LINES is no longer supported - removed legacy code
                    line_filtered = False

                    code_lines = code_content.split("\n")

                    if (
                        should_chunk_content(
                            code_content, SEARCH_CONFIG["chunking_threshold"]
                        )
                        and not line_filtered
                    ):
                        chunks = chunk_large_code_clean(
                            code_content,
                            file_start_line=start_line or 1,
                            max_lines=SEARCH_CONFIG["chunk_size"],
                            chunk_threshold=SEARCH_CONFIG["chunking_threshold"],
                        )

                        for chunk in chunks:
                            chunked_result = result_dict.copy()
                            chunked_result["code_snippet"] = chunk["content"]

                            chunk_info = create_chunk_info(chunk)

                            beautified_result = beautify_node_result(
                                chunked_result,
                                i,
                                include_code=True,
                                total_nodes=total_nodes,
                                chunk_info=chunk_info,
                            )

                            result_data = beautified_result

                            # Collect delivery item
                            delivery_items.append(
                                {
                                    "type": "tool_use",
                                    "tool_name": "database",
                                    "query_name": base_query_name,
                                    "query": final_params,
                                    "node_index": i,
                                    "total_nodes": total_nodes,
                                    "chunk_info": chunk_info,
                                    "data": result_data,
                                    "include_code": include_code,
                                    "chunk_index": chunk["chunk_num"] - 1,
                                    "total_items": len(chunks),
                                }
                            )
                    else:
                        # No chunking needed for this node - process directly
                        beautified_result = beautify_node_result(
                            result_dict, i, include_code=True, total_nodes=total_nodes
                        )

                        result_data = beautified_result

                        # Collect delivery item
                        delivery_items.append(
                            {
                                "type": "tool_use",
                                "tool_name": "database",
                                "query_name": base_query_name,
                                "query": final_params,
                                "node_index": i,
                                "total_nodes": total_nodes,
                                "data": result_data,
                                "include_code": include_code,
                                "total_items": total_nodes,
                            }
                        )
                else:
                    beautified_result = beautify_node_result(
                        result_dict, i, include_code=True, total_nodes=total_nodes
                    )

                    result_data = beautified_result

                    # Collect delivery item
                    delivery_items.append(
                        {
                            "type": "tool_use",
                            "tool_name": "database",
                            "query_name": base_query_name,
                            "query": final_params,
                            "node_index": i,
                            "total_nodes": total_nodes,
                            "data": result_data,
                            "include_code": include_code,
                            "total_items": total_nodes,
                        }
                    )

            # Register delivery queue and get first batch with line limit for guidance
            first_item = register_delivery_queue_and_get_first_batch_with_line_limit(
                "database", action.parameters, delivery_items, "database"
            )
            if first_item:
                yield first_item
    except Exception as e:
        error_msg = f"Database query execution failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        yield {
            "type": "tool_use",
            "tool_name": "database",
            "query_name": query_name,
            "query": action.parameters,
            "error": error_msg,
            "include_code": code_snippet,
        }


def execute_database_action(
    action: AgentAction, context: str = "agent"
) -> Iterator[Dict[str, Any]]:
    logger.debug(f"🔍 Database action triggered with parameters: {action.parameters}")
    if "query_name" in action.parameters:
        yield from execute_structured_database_query(action, context)
        return

    yield {
        "type": "tool_use",
        "tool_name": "database",
        "query_name": "unknown",
        "query": action.parameters,
        "error": "Database action requires 'query_name' parameter",
        "include_code": False,
    }


# Alias for consistency with new naming convention
execute_database_search_action = execute_database_action


def process_metadata_only_results(results: List[Any], total_nodes: int) -> List[str]:
    """
    Process results for metadata-only scenarios.

    Args:
        results: List of raw results
        total_nodes: Total number of nodes

    Returns:
        List of beautified result strings
    """
    processed_results = []

    for i, row in enumerate(results, 1):
        # Handle both SQLite Row objects and dictionaries
        if hasattr(row, "keys"):
            result_dict = dict(row)
        else:
            result_dict = row

        # Ensure result_dict is a dictionary
        if not isinstance(result_dict, dict):
            result_dict = dict(result_dict)

        cleaned_dict = clean_result_dict(result_dict)

        beautified_result = beautify_node_result_metadata_only(
            cleaned_dict, i, total_nodes=total_nodes
        )
        processed_results.append(beautified_result)

    return processed_results


def clean_result_dict(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove unnecessary fields from result dictionary.

    Args:
        result_dict: Raw result dictionary

    Returns:
        Cleaned result dictionary
    """
    cleaned = result_dict.copy()

    # Remove unnecessary fields (but preserve start_line, end_line, and other essential fields)
    for field in ["project_id", "project_name", "language", "file_size"]:
        cleaned.pop(field, None)

    return cleaned
