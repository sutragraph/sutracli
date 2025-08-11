from loguru import logger
from typing import Iterator, Dict, Any, List, Optional
from graph.graph_operations import GraphOperations
import subprocess
from services.agent.delivery_management import delivery_manager
from tools.utils import (
    beautify_node_result,
    chunk_large_code_clean,
)
from queries.agent_queries import (
    GET_FILE_BY_ID,
    GET_FILE_BLOCK_SUMMARY,
    GET_CHILD_BLOCKS,
    GET_PARENT_BLOCK,
    GET_FILE_IMPORTS,
    GET_DEPENDENCY_CHAIN,
)
from tools.utils.formatting_utils import beautify_node_result_metadata_only
from pathlib import Path
import os
import json
from models.agent import AgentAction
from tools.guidance_builder import DatabaseSearchGuidance
from tools.utils.constants import (
    SEARCH_CONFIG,
    DATABASE_QUERY_CONFIG,
    DATABASE_ERROR_GUIDANCE,
    DELIVERY_QUEUE_CONFIG,
    GUIDANCE_MESSAGES,
)
from services.agent.delivery_management import delivery_manager

# Initialize guidance handler
guidance_handler = DatabaseSearchGuidance()

def _generate_error_guidance(query_name: str, params: dict) -> str:
    """Generate dynamic error guidance based on query type and parameters."""
    guidance_parts = []

    # Check for file_path parameter
    if "file_path" in params:
        file_path = params["file_path"]
        guidance_parts.append(
            f"Ensure file_path '{file_path}' is case-sensitive and the complete correct path (format: /path/to/file). "
            "If the path is correct, try using different search methods like semantic_search."
        )

    # Check for function_name parameter
    if "function_name" in params:
        function_name = params["function_name"]
        guidance_parts.append(
            f"Ensure function_name '{function_name}' is spelled correctly and exists in the codebase. "
            "Try using semantic_search to find similar function names."
        )

    # Check for name parameter (for exact name searches)
    if "name" in params:
        name = params["name"]
        guidance_parts.append(
            f"Ensure name '{name}' is spelled correctly and exists. "
            "Try using semantic_search for partial matches or similar names."
        )

    # Query-specific guidance using constants
    if query_name in DATABASE_ERROR_GUIDANCE:
        guidance_parts.append(DATABASE_ERROR_GUIDANCE[query_name])

    # General guidance
    guidance_parts.append(
        "Do not use these same parameters again as no data found in database. "
        "Try different methods or different parameters."
    )

    return " ".join(guidance_parts)

def execute_structured_database_query(
    action: AgentAction, context: str = "agent"
) -> Iterator[Dict[str, Any]]:
    # Initialize variables for exception handling
    query_name = action.parameters.get("query_name", "unknown")
    code_snippet = action.parameters.get("code_snippet", True)

    try:
        # Get graph operations instance
        graph_ops = GraphOperations()

        # Check if this is a fetch_next_code request (unified for chunks and nodes)
        fetch_response = handle_fetch_next_request(
            "database", action.parameters, "query_complete"
        )
        if fetch_response:
            yield fetch_response
            return
        query_params = {
            k: v
            for k, v in action.parameters.items()
            if k not in ["query_name", "code_snippet", "fetch_next_code"]
        }

        logger.debug(f"🗄️ Executing structured query: {query_name}")
        logger.debug(f"📋 Query parameters: {query_params}")
        logger.debug(f"🔧 Code snippet mode: {code_snippet}")

        query_config = {}
        sql_mapping = {
            "GET_FILE_BY_PATH": GET_FILE_BY_ID,
            "GET_FILE_BLOCK_SUMMARY": GET_FILE_BLOCK_SUMMARY,
            "GET_CHILD_BLOCKS": GET_CHILD_BLOCKS,
            "GET_PARENT_BLOCK": GET_PARENT_BLOCK,
            "GET_FILE_IMPORTS": GET_FILE_IMPORTS,
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
            file_path = final_params.get("file_path")
            if file_path:
                file_id = graph_ops._get_file_id_by_path(file_path)
                if file_id:
                    results = graph_ops.connection.execute_query(sql_query, (file_id,))
                else:
                    results = []
            else:
                results = []
        else:
            # For other queries, convert dict params to tuple based on query requirements
            if base_query_name == "GET_FILE_BLOCK_SUMMARY":
                file_id = final_params.get("file_id")
                results = (
                    graph_ops.connection.execute_query(sql_query, (file_id,))
                    if file_id
                    else []
                )
            elif base_query_name in ["GET_FILE_IMPORTS", "GET_DEPENDENCY_CHAIN"]:
                # These queries now take file_path and convert to file_id internally
                file_path = final_params.get("file_path")
                if file_path:
                    file_id = graph_ops._get_file_id_by_path(file_path)
                    if file_id:
                        if base_query_name == "GET_DEPENDENCY_CHAIN":
                            depth = final_params.get("depth", 5)
                            results = graph_ops.connection.execute_query(
                                sql_query, (file_id, depth)
                            )
                        else:
                            results = graph_ops.connection.execute_query(
                                sql_query, (file_id,)
                            )
                    else:
                        results = []
                else:
                    results = []
            elif base_query_name == "GET_CHILD_BLOCKS":
                parent_block_id = final_params.get("parent_block_id")
                results = (
                    graph_ops.connection.execute_query(sql_query, (parent_block_id,))
                    if parent_block_id
                    else []
                )
            elif base_query_name == "GET_PARENT_BLOCK":
                block_id = final_params.get("block_id")
                results = (
                    graph_ops.connection.execute_query(sql_query, (block_id,))
                    if block_id
                    else []
                )
            else:
                results = []
        logger.debug(f"📊 Query returned {len(results)} results")

        # Get project_id for connection lookup from the first result if available
        current_project_id = None
        if results and len(results) > 0:
            # Try to get project_id from the first result
            first_result = results[0]
            if isinstance(first_result, dict) and "project_id" in first_result:
                current_project_id = first_result["project_id"]
                logger.debug(
                    f"🔗 Using project_id {current_project_id} for connection lookup"
                )
            else:
                logger.debug(
                    "🔗 No project_id found in database results for connection lookup"
                )
        else:
            logger.debug("🔗 No results available for project_id extraction")

        # Yield tool usage information for logging
        search_term = query_params.get(
            "name",
            query_params.get(
                "function_name",
                query_params.get("file_path", query_params.get("keyword", "unknown")),
            ),
        )
        yield {
            "type": "tool_use",
            "tool_name": "database",
            "query": search_term,
            "query_name": base_query_name,
            "result": f"Found {len(results)} nodes",
        }

        if not results:
            # For GET_FILE_BY_PATH, try ripgrep fallback to find similar file names
            if base_query_name == "GET_FILE_BY_PATH" and "file_path" in final_params:
                file_path = final_params["file_path"]
                filename = os.path.basename(file_path)
                logger.debug(f"🔄 Trying ripgrep fallback for file: {filename}")

                # Use ripgrep to search for the filename
                try:
                    cmd = ["rg", "-l", "--fixed-strings", filename]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, cwd="."
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        found_files = result.stdout.strip().split("\n")
                        logger.debug(
                            f"✅ Ripgrep found {len(found_files)} files with similar names"
                        )
                        # Try to get file_id for the first found file
                        for found_file in found_files[:3]:  # Try first 3 matches
                            file_id = graph_ops._get_file_id_by_path(found_file)
                            if file_id:
                                results = graph_ops.connection.execute_query(
                                    sql_query, (file_id,)
                                )
                                if results:
                                    logger.debug(
                                        f"✅ Found file data using ripgrep match: {found_file}"
                                    )
                                    break
                    else:
                        logger.debug("❌ Ripgrep fallback found no matching files")
                except Exception as e:
                    logger.debug(f"❌ Ripgrep fallback failed: {e}")

            if not results:
                no_results_guidance = guidance_handler._build_guidance_message(
                    search_type="database",
                    scenario="NO_RESULTS_FOUND",
                )

                # Generate additional dynamic error guidance based on query parameters
                error_guidance = _generate_error_guidance(query_name, final_params)

                # Combine both guidance messages
                combined_guidance = (
                    f"{no_results_guidance}\n\n{error_guidance}"
                    if no_results_guidance
                    else error_guidance
                )

                yield {
                    "type": "tool_use",
                    "tool_name": "database",
                    "query_name": query_name,
                    "query": final_params,
                    "result": "result found: 0",
                    "data": combined_guidance,
                    "include_code": include_code,
                    "total_nodes": 0,
                }
                return
        # Get delivery status for guidance
        delivery_info = delivery_manager.get_next_item_info(
            "database", action.parameters
        )

        # Initialize guidance message - will be built after processing
        guidance_message = ""

        total_nodes = len(results)

        # Handle different scenarios based on include_code and number of results
        if not include_code:
            # Use delivery queue for metadata-only results
            batch_size = DELIVERY_QUEUE_CONFIG["database_metadata_only"]
            batches = guidance_handler._create_delivery_batches(results, batch_size=batch_size)

            for batch_num, batch in enumerate(batches, 1):
                delivery_info = guidance_handler._build_delivery_info(
                    current_batch=batch_num,
                    total_batches=len(batches),
                    batch_size=batch_size,
                    total_results=total_nodes,
                    has_code=False,
                )

                # Build guidance message for this batch
                guidance_message = guidance_handler._format_delivery_guidance(delivery_info, "database")

                if delivery_info["has_more"]:
                    guidance_message += GUIDANCE_MESSAGES["FETCH_NEXT_CODE_NOTE"]

                # Process metadata-only results for this batch
                processed_batch = process_metadata_only_results(batch, len(batch))

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
                    "data": guidance_message + "\n\n" + processed_batch,
                    "include_code": include_code,
                    "result": f"Found {total_nodes} nodes",
                    "current_batch": batch_num,
                    "total_batches": len(batches),
                    "has_more_batches": batch_num < len(batches),
                }
            return

        elif len(results) == 1:
            # Single result with code - check if chunking is needed
            row = results[0]
            result_dict = dict(row) if hasattr(row, "keys") else row
            result_dict = clean_result_dict(result_dict)

            # For GET_FILE_BY_PATH, the content is in 'content' field, for other queries it's in 'code_snippet'
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

                # Check if chunking is needed for single result (but not for line-filtered results)
                code_lines = code_content.split("\n")
                if (
                    should_chunk_content(
                        code_content, SEARCH_CONFIG["chunking_threshold"]
                    )
                    and not line_filtered
                ):
                    # Single result with chunking needed - use delivery manager
                    # Check if we have a pending delivery for this query
                    next_item = check_pending_delivery("database", action.parameters)
                    if next_item is not None:
                        yield next_item
                        return

                    # Process chunks directly
                    all_delivery_items = []
                    chunks = chunk_large_code_clean(
                        code_content,
                        file_start_line=start_line or 1,
                        max_lines=SEARCH_CONFIG["chunk_size"],
                    )

                    code_lines = code_content.split("\n")
                    for chunk in chunks:
                        chunked_result = result_dict.copy()
                        chunked_result["code_snippet"] = chunk["content"]

                        chunk_info = create_chunk_info(chunk)

                        # Build chunk-specific guidance message
                        chunk_scenario = guidance_handler._determine_guidance_scenario(
                            total_nodes=1,
                            include_code=True,
                            code_lines=len(code_lines),
                            chunk_info=chunk_info,
                        )

                        chunk_guidance = guidance_handler._build_guidance_message(
                            search_type="database",
                            scenario=chunk_scenario,
                            total_lines=len(code_lines),
                            chunk_start=chunk_info["chunk_start_line"],
                            chunk_end=chunk_info["chunk_end_line"],
                            chunk_num=chunk_info["chunk_num"],
                            total_chunks=chunk_info["total_chunks"],
                        )

                        if chunk_guidance:
                            chunk_guidance += "\n\n"

                        beautified_result = beautify_node_result(
                            chunked_result,
                            1,
                            include_code=True,
                            total_nodes=1,
                            chunk_info=chunk_info,
                        )

                        result_data = chunk_guidance + beautified_result

                        # Create delivery item
                        all_delivery_items.append(
                            {
                                "type": "tool_use",
                                "tool_name": "database",
                                "query_name": base_query_name,
                                "query": final_params,
                                "result": f"result found: 1",
                                "chunk_info": chunk_info,
                                "data": result_data,
                                "include_code": True,
                                "total_nodes": 1,
                            }
                        )

                    # Register and deliver first item
                    first_item = register_and_deliver_first_item(
                        "database", action.parameters, all_delivery_items
                    )
                    if first_item:
                        yield first_item
                    return
                else:
                    # Single result with small code - no chunking needed
                    # Prepare guidance parameters for line-filtered queries
                    guidance_params = {
                        "total_lines": len(code_lines),
                    }

                    # Note: GET_CODE_FROM_FILE_LINES is no longer supported - removed legacy code

                    # Use shared guidance function with line-filtering parameters
                    guidance_message = guidance_handler._build_batch_guidance_message(
                        search_type="database",
                        total_nodes=1,
                        include_code=True,
                        has_large_files=False,
                        current_node=1,
                        has_more_nodes=False,
                        is_line_filtered=line_filtered,
                        code_lines=len(code_lines),
                        **guidance_params,
                    )

                    beautified_result = beautify_node_result(
                        result_dict,
                        1,
                        include_code=True,
                        total_nodes=1,
                    )

                    # Send single batch result for small files
                    result_data = (
                        guidance_message + "\n\n" + beautified_result
                        if guidance_message
                        else beautified_result
                    )

                    yield {
                        "type": "tool_use",
                        "tool_name": "database",
                        "query_name": base_query_name,
                        "query": final_params,
                        "result": f"result found",
                        "data": result_data,
                        "include_code": include_code,
                        "total_nodes": 1,
                    }
                    return
            else:
                # No code content available - use proper guidance scenario
                missing_content_guidance = guidance_handler._build_guidance_message(
                    search_type="database",
                    scenario="NODE_MISSING_CODE_CONTENT",
                )
                guidance_message = (
                    missing_content_guidance + "\n\n"
                    if missing_content_guidance
                    else ""
                )

                beautified_result = beautify_node_result(
                    result_dict, 1, include_code=True, total_nodes=1
                )

                # Send single batch result for missing code
                result_data = guidance_message + beautified_result

                yield {
                    "type": "tool_use",
                    "tool_name": "database",
                    "query_name": base_query_name,
                    "query": final_params,
                    "result": f"result found",
                    "data": result_data,
                    "include_code": include_code,
                    "total_nodes": 1,
                }
                return

        else:
            # Multiple results with code - use delivery manager for sequential delivery
            # Check if we have a pending delivery for this query
            next_item = check_pending_delivery("database", action.parameters)
            if next_item is not None:
                yield next_item
                return

            # No pending delivery - collect all items and register them
            all_delivery_items = []

            for i, row in enumerate(results, 1):
                result_dict = dict(row) if hasattr(row, "keys") else row
                result_dict = clean_result_dict(result_dict)

                # For GET_FILE_BY_PATH, the content is in 'content' field, for other queries it's in 'code_snippet'
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
                        )

                        for chunk in chunks:
                            chunk_info = create_chunk_info(chunk)

                            # Build sequential node guidance message
                            sequential_scenario = guidance_handler._determine_sequential_node_scenario(
                                chunk_info=chunk_info,
                            )

                            chunk_guidance = guidance_handler._build_sequential_node_message(
                                scenario=sequential_scenario,
                                node_index=i,
                                total_nodes=total_nodes,
                                total_lines=len(code_lines),
                                chunk_num=chunk_info["chunk_num"],
                                total_chunks=chunk_info["total_chunks"],
                                chunk_start=chunk_info["chunk_start_line"],
                                chunk_end=chunk_info["chunk_end_line"],
                            )

                            if chunk_guidance:
                                chunk_guidance += "\n\n"

                            chunked_result = result_dict.copy()
                            chunked_result["code_snippet"] = chunk["content"]

                            beautified_result = beautify_node_result(
                                chunked_result,
                                i,
                                include_code=True,
                                total_nodes=total_nodes,
                                chunk_info=chunk_info,
                            )

                            result_data = chunk_guidance + beautified_result

                            # Collect item for delivery manager
                            all_delivery_items.append(
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
                                }
                            )
                    else:
                        # No chunking needed for this node - process directly
                        # For sequential processing, we need to check if this is truly the last node
                        # that will be delivered. Since we're collecting all items first,
                        # we know this is the last node if it's the last in the result set.
                        # Build sequential node guidance message
                        sequential_scenario = guidance_handler._determine_sequential_node_scenario()

                        node_guidance = guidance_handler._build_sequential_node_message(
                            scenario=sequential_scenario,
                            node_index=i,
                            total_nodes=total_nodes,
                            total_lines=len(code_lines),
                        )

                        if node_guidance:
                            node_guidance += "\n\n"

                        beautified_result = beautify_node_result(
                            result_dict, i, include_code=True, total_nodes=total_nodes
                        )

                        result_data = node_guidance + beautified_result

                        # Collect item for delivery manager
                        all_delivery_items.append(
                            {
                                "type": "tool_use",
                                "tool_name": "database",
                                "query_name": base_query_name,
                                "query": final_params,
                                "node_index": i,
                                "total_nodes": total_nodes,
                                "data": result_data,
                                "include_code": include_code,
                            }
                        )
                else:
                    # No code content available - use proper enum scenario
                    sequential_scenario = "NODE_NO_CODE_CONTENT"

                    node_guidance = guidance_handler._build_sequential_node_message(
                        scenario=sequential_scenario,
                        node_index=i,
                        total_nodes=total_nodes,
                    )

                    if node_guidance:
                        node_guidance += "\n\n"

                    beautified_result = beautify_node_result(
                        result_dict, i, include_code=True, total_nodes=total_nodes
                    )
                    result_data = node_guidance + beautified_result

                    # Collect item for delivery manager
                    all_delivery_items.append(
                        {
                            "type": "tool_use",
                            "tool_name": "database",
                            "query_name": base_query_name,
                            "query": final_params,
                            "node_index": i,
                            "total_nodes": total_nodes,
                            "data": result_data,
                            "include_code": include_code,
                        }
                    )

            # Register and deliver first item using common utility
            first_item = register_and_deliver_first_item(
                "database", action.parameters, all_delivery_items
            )
            if first_item:
                yield first_item
            else:
                # No items to deliver - use common utility
                response = create_no_items_response(
                    "database", final_params, len(results), include_code
                )
                yield response
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


def create_chunk_info(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized chunk info dictionary.

    Args:
        chunk: Chunk data from chunk_large_code_clean

    Returns:
        Standardized chunk info dictionary
    """
    return {
        "chunk_num": chunk["chunk_num"],
        "total_chunks": chunk["total_chunks"],
        "chunk_start_line": chunk.get("chunk_start_line", chunk.get("start_line")),
        "chunk_end_line": chunk.get("chunk_end_line", chunk.get("end_line")),
        "total_lines": chunk["total_lines"],
    }


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


def handle_fetch_next_request(
    action_type: str,
    action_parameters: Dict[str, Any],
    response_type: str = "query_complete",
) -> Optional[Dict[str, Any]]:
    """
    Handle fetch_next_code requests (unified for both chunks and nodes).

    Args:
        action_type: Type of action ("database" or "semantic_search")
        action_parameters: Action parameters
        response_type: Response type for completion message

    Returns:
        Dict with next item or completion message, None if not a fetch request
    """
    if not action_parameters.get("fetch_next_code", False):
        return None

    logger.debug(f"🔄 fetch_next_code request detected")

    # Use existing delivery queue if:
    # 1. No query is provided (just fetch_next_code), OR
    # 2. Same query is provided (query matches existing queue)
    query_provided = action_parameters.get("query")

    if not query_provided:
        logger.debug(
            "🔄 No query provided - using existing delivery queue for fetch_next_code"
        )
        next_item = delivery_manager.get_next_item_from_existing_queue()
    else:
        # Check if this query matches the existing queue
        current_signature = delivery_manager._generate_query_signature(
            action_type, action_parameters
        )
        if delivery_manager._last_query_signature == current_signature:
            logger.debug(
                "🔄 Same query provided - using existing delivery queue for fetch_next_code"
            )
            next_item = delivery_manager.get_next_item_from_existing_queue()
        else:
            logger.debug(
                "🔄 Different query provided with fetch_next_code - treating as new query"
            )
            next_item = delivery_manager.get_next_item(action_type, action_parameters)

    if next_item:
        return next_item
    else:
        # No more items available
        base_response = {
            "result": "result found: 0",
            "include_code": True,
            "total_nodes": 0,
        }

        if action_type == "database":
            return {
                "type": f"tool_use",
                "tool_name": "database",
                "query_name": "fetch_next_code",
                "query": action_parameters,
                "data": f"No more code chunks available. All items from the previous query have been delivered.",
                **base_response,
            }
        else:  # semantic_search
            return {
                "type": f"tool_use",
                "tool_name": "semantic_search",
                "query": "fetch_next_code",
                "data": f"No more code chunks/nodes available. All items from the previous query have been delivered.",
                "code_snippet": True,
                **base_response,
            }


def register_and_deliver_first_item(
    action_type: str,
    action_parameters: Dict[str, Any],
    delivery_items: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Register delivery queue and get first item.

    Args:
        action_type: Type of action ("database" or "semantic_search")
        action_parameters: Action parameters
        delivery_items: List of items to register for delivery

    Returns:
        First item from delivery queue or None if no items
    """
    if not delivery_items:
        return None

    delivery_manager.register_delivery_queue(
        action_type, action_parameters, delivery_items
    )
    return delivery_manager.get_next_item(action_type, action_parameters)


def check_pending_delivery(
    action_type: str, action_parameters: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Check if there's a pending delivery for this query.

    Args:
        action_type: Type of action ("database" or "semantic_search")
        action_parameters: Action parameters

    Returns:
        Next pending item or None if no pending delivery
    """
    return delivery_manager.get_next_item(action_type, action_parameters)


def create_no_items_response(
    action_type: str,
    action_parameters: Dict[str, Any],
    total_results: int,
    include_code: bool = True,
) -> Dict[str, Any]:
    """
    Create response when no deliverable items are found.

    Args:
        action_type: Type of action ("database" or "semantic_search")
        action_parameters: Action parameters
        total_results: Total number of results found
        include_code: Whether code was requested

    Returns:
        Response dictionary for no items scenario
    """
    base_response = {
        "result": f"result found: {total_results}",
        "data": "No deliverable items found.",
        "total_nodes": total_results,
    }

    if action_type == "database":
        query_name = action_parameters.get("query_name", "unknown")
        return {
            "type": "tool_use",
            "tool_name": "database",
            "query_name": query_name,
            "query": action_parameters,
            "include_code": include_code,
            **base_response,
        }
    else:  # semantic_search
        query = action_parameters.get("query", "")
        return {
            "type": "tool_use",
            "tool_name": "semantic_search",
            "query": query,
            "code_snippet": include_code,
            **base_response,
        }


def clean_result_dict(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove unnecessary fields from result dictionary.

    Args:
        result_dict: Raw result dictionary

    Returns:
        Cleaned result dictionary
    """
    cleaned = result_dict.copy()

    # Remove unnecessary fields
    for field in ["project_id", "project_name", "language", "file_size"]:
        cleaned.pop(field, None)

    return cleaned


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
        result_dict = dict(row) if hasattr(row, "keys") else row
        cleaned_dict = clean_result_dict(result_dict)

        beautified_result = beautify_node_result_metadata_only(
            cleaned_dict, i, total_nodes=total_nodes
        )
        processed_results.append(beautified_result)

    return processed_results
