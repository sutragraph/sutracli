from loguru import logger
from typing import Iterator, Dict, Any
from src.services.agent.tool_action_executor.utils import (
    beautify_node_result,
    process_code_with_line_filtering,
    chunk_large_code_clean,
    handle_fetch_next_request,
    register_and_deliver_first_item,
    check_pending_delivery,
    create_no_items_response,
    clean_result_dict,
    process_metadata_only_results,
)
from src.services.agent.tool_action_executor.utils.chunk_processing_utils import (
    create_chunk_info,
    should_chunk_content,
)
from src.services.agent.tool_action_executor.utils.search_utils import (
    build_batch_guidance_message,
)
from src.queries.agent_queries import (
    GET_NODES_BY_EXACT_NAME,
    GET_NODES_BY_NAME_LIKE,
    GET_NODES_BY_KEYWORD_SEARCH,
    GET_CODE_FROM_FILE,
    GET_ALL_NODE_NAMES_FROM_FILE,
    GET_FUNCTION_CALLERS,
    GET_FUNCTION_CALLEES,
    GET_FILE_DEPENDENCIES,
)
from src.services.agent.agentic_core import AgentAction
from src.services.agent.agent_prompt.guidance_builder import (
    SearchType,
    determine_guidance_scenario,
    determine_sequential_node_scenario,
    build_guidance_message,
    build_sequential_node_message,
)
from src.services.agent.tool_action_executor.utils.constants import (
    SEARCH_CONFIG,
    DATABASE_QUERY_CONFIG,
    DATABASE_ERROR_GUIDANCE,
    DELIVERY_QUEUE_CONFIG,
    GUIDANCE_MESSAGES,
)
from src.services.agent.delivery_management import delivery_manager
from src.services.agent.tool_action_executor.utils.search_utils import (
    process_keyword_search_results,
    create_delivery_batches,
    build_delivery_info,
    format_delivery_guidance,
)


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
    action: AgentAction, db_connection=None
) -> Iterator[Dict[str, Any]]:
    # Initialize variables for exception handling
    query_name = action.parameters.get("query_name", "unknown")
    code_snippet = action.parameters.get("code_snippet", True)

    try:
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

        # Build query configuration using constants and SQL imports
        query_config = {}
        sql_mapping = {
            "GET_NODES_BY_EXACT_NAME": GET_NODES_BY_EXACT_NAME,
            "GET_NODES_BY_KEYWORD_SEARCH": GET_NODES_BY_KEYWORD_SEARCH,
            "GET_CODE_FROM_FILE": GET_CODE_FROM_FILE,
            "GET_CODE_FROM_FILE_LINES": GET_CODE_FROM_FILE,
            "GET_ALL_NODE_NAMES_FROM_FILE": GET_ALL_NODE_NAMES_FROM_FILE,
            "GET_FUNCTION_CALLERS": GET_FUNCTION_CALLERS,
            "GET_FUNCTION_CALLEES": GET_FUNCTION_CALLEES,
            "GET_FILE_DEPENDENCIES": GET_FILE_DEPENDENCIES,
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
                "type": "database_query_error",
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
                    "type": "database_query_error",
                    "tool_name": "database",
                    "query_name": base_query_name,
                    "query": query_params,
                    "error": error_msg,
                    "include_code": include_code,
                }
                return

            # Fix file path parameter - prepend current directory if path doesn't start with current dir
            if param == "file_path":
                from pathlib import Path
                import os

                file_path = query_params[param]
                current_dir = Path.cwd()
                file_path_obj = Path(file_path)

                # Check if file path starts with current directory
                try:
                    # If file_path is relative to current dir, this will work
                    file_path_obj.relative_to(current_dir)
                    # Path is already relative to current dir, use as is
                    final_params[param] = str(file_path_obj)
                except ValueError:
                    # Path is not relative to current dir, concatenate with current dir
                    fixed_path = current_dir / file_path
                    final_params[param] = str(fixed_path)
                    logger.debug(f"🔧 Fixed file path: {query_params[param]} -> {fixed_path}")
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
        cursor = db_connection.connection.cursor()
        cursor.execute(sql_query, final_params)
        columns = (
            [description[0] for description in cursor.description]
            if cursor.description
            else []
        )
        rows = cursor.fetchall()
        results = [dict(zip(columns, row)) for row in rows]
        logger.debug(f"📊 Query returned {len(results)} results")

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
            # Try fallback with LIKE operator for exact name queries
            if base_query_name == "GET_NODES_BY_EXACT_NAME" and "name" in final_params:
                logger.debug(
                    f"🔄 Trying LIKE fallback for exact name query: {final_params['name']}"
                )

                # Use the fallback query with LIKE operator
                fallback_cursor = db_connection.connection.cursor()
                fallback_cursor.execute(GET_NODES_BY_NAME_LIKE, final_params)
                fallback_columns = (
                    [description[0] for description in fallback_cursor.description]
                    if fallback_cursor.description
                    else []
                )
                fallback_rows = fallback_cursor.fetchall()
                fallback_results = [
                    dict(zip(fallback_columns, row)) for row in fallback_rows
                ]

                if fallback_results:
                    logger.debug(
                        f"✅ LIKE fallback successful: {len(fallback_results)} results"
                    )
                    results = fallback_results
                    # Update query name to indicate fallback was used
                    base_query_name = "GET_NODES_BY_NAME_LIKE"
                else:
                    logger.debug("❌ LIKE fallback also returned 0 results")

            # Try fallback for GET_CODE_FROM_FILE and GET_CODE_FROM_FILE_LINES using filename with GET_NODES_BY_EXACT_NAME
            if (
                not results
                and base_query_name
                in ["GET_CODE_FROM_FILE", "GET_CODE_FROM_FILE_LINES"]
                and "file_path" in final_params
            ):
                import os

                original_path = final_params["file_path"]
                # Extract filename from path (last element after splitting by '/')
                filename = os.path.basename(original_path)

                logger.debug(
                    f"🔄 Trying GET_NODES_BY_EXACT_NAME fallback for {base_query_name} with filename: {filename}"
                )

                # Use GET_NODES_BY_EXACT_NAME with the extracted filename
                filename_fallback_cursor = db_connection.connection.cursor()
                filename_fallback_params = {
                    "name": filename,
                    "project_id": final_params.get("project_id"),
                }
                filename_fallback_cursor.execute(
                    GET_NODES_BY_EXACT_NAME, filename_fallback_params
                )
                filename_fallback_columns = (
                    [
                        description[0]
                        for description in filename_fallback_cursor.description
                    ]
                    if filename_fallback_cursor.description
                    else []
                )
                filename_fallback_rows = filename_fallback_cursor.fetchall()
                filename_fallback_results = [
                    dict(zip(filename_fallback_columns, row))
                    for row in filename_fallback_rows
                ]

                if filename_fallback_results:
                    logger.debug(
                        f"✅ GET_NODES_BY_EXACT_NAME fallback successful: {len(filename_fallback_results)} results"
                    )
                    results = filename_fallback_results
                    # Update query name to indicate fallback was used
                    base_query_name = "GET_NODES_BY_EXACT_NAME"
                else:
                    logger.debug(
                        "❌ GET_NODES_BY_EXACT_NAME fallback also returned 0 results"
                    )

            # Try fallback with system directory for file path queries
            if not results and "file_path" in final_params:
                import os

                original_path = final_params["file_path"]
                system_dir = os.getcwd()

                # Remove ./ prefix if present to avoid double path issues
                clean_path = (
                    original_path[2:]
                    if original_path.startswith("./")
                    else original_path
                )

                system_fallback_path = os.path.join(system_dir, clean_path).replace(
                    "\\", "/"
                )
                logger.debug(
                    f"🔄 Trying fallback with system dir: {system_fallback_path}"
                )

                system_fallback_params = final_params.copy()
                system_fallback_params["file_path"] = system_fallback_path

                cursor.execute(sql_query, system_fallback_params)
                system_fallback_rows = cursor.fetchall()
                system_fallback_results = [
                    dict(zip(columns, row)) for row in system_fallback_rows
                ]

                if system_fallback_results:
                    logger.debug(
                        f"✅ System directory fallback successful: {len(system_fallback_results)} results"
                    )
                    results = system_fallback_results
                    final_params = system_fallback_params
                else:
                    logger.debug("❌ System directory fallback also returned 0 results")

            if not results:
                # Use proper guidance scenario for no results
                from src.services.agent.agent_prompt.guidance_builder import (
                    GuidanceScenario,
                )

                no_results_guidance = build_guidance_message(
                    search_type=SearchType.DATABASE,
                    scenario=GuidanceScenario.NO_RESULTS_FOUND,
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

        # Special handling for keyword search with delivery queue
        if base_query_name == "GET_NODES_BY_KEYWORD_SEARCH":
            keyword = final_params.get("keyword", "")

            if include_code:
                # Process results with context extraction
                processed_results = process_keyword_search_results(
                    results, keyword, context_lines=10
                )

                # Create delivery batches using config
                batch_size = DELIVERY_QUEUE_CONFIG["keyword_search_with_code"]
                batches = create_delivery_batches(
                    processed_results, batch_size=batch_size
                )

                for batch_num, batch in enumerate(batches, 1):
                    delivery_info = build_delivery_info(
                        current_batch=batch_num,
                        total_batches=len(batches),
                        batch_size=batch_size,
                        total_results=total_nodes,
                        has_code=True,
                    )

                    guidance_message = format_delivery_guidance(
                        delivery_info, "keyword"
                    )

                    # Format batch results
                    batch_data = []
                    for result in batch:
                        batch_data.append(
                            {
                                "node_id": result.get("node_id"),
                                "node_type": result.get("node_type"),
                                "name": result.get("name"),
                                "file_path": result.get("file_path"),
                                "code_context": result.get("code_snippet", ""),
                                "keyword_found": keyword,
                            }
                        )

                    yield {
                        "type": "tool_use",
                        "tool_name": "database",
                        "query_name": base_query_name,
                        "query": final_params,
                        "data": guidance_message
                        + "\n\n"
                        + "\n\n".join(
                            [
                                f"=== Node {result['node_id']}: {result['name']} ===\n"
                                f"File: {result['file_path']}\n"
                                f"Type: {result['node_type']}\n\n"
                                f"{result['code_context']}"
                                for result in batch_data
                            ]
                        ),
                        "include_code": include_code,
                        "result": f"Found {total_nodes} nodes",
                        "current_batch": batch_num,
                        "total_batches": len(batches),
                        "has_more_batches": batch_num < len(batches),
                    }
                return
            else:
                # Metadata only - use config batch size
                batch_size = DELIVERY_QUEUE_CONFIG["keyword_search_metadata"]
                batches = create_delivery_batches(results, batch_size=batch_size)

                for batch_num, batch in enumerate(batches, 1):
                    delivery_info = build_delivery_info(
                        current_batch=batch_num,
                        total_batches=len(batches),
                        batch_size=batch_size,
                        total_results=total_nodes,
                        has_code=False,
                    )

                    guidance_message = format_delivery_guidance(
                        delivery_info, "keyword"
                    )

                    # Process metadata-only results
                    processed_batch = process_metadata_only_results(batch, len(batch))

                    # Ensure processed_batch is a string
                    if isinstance(processed_batch, list):
                        processed_batch = "\n".join(
                            str(item) for item in processed_batch
                        )
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

        # Handle different scenarios based on include_code and number of results
        if not include_code:
            # Use delivery queue for metadata-only results
            batch_size = DELIVERY_QUEUE_CONFIG["database_metadata_only"]
            batches = create_delivery_batches(results, batch_size=batch_size)

            for batch_num, batch in enumerate(batches, 1):
                delivery_info = build_delivery_info(
                    current_batch=batch_num,
                    total_batches=len(batches),
                    batch_size=batch_size,
                    total_results=total_nodes,
                    has_code=False,
                )

                # Build guidance message for this batch
                guidance_message = f"DATABASE SEARCH RESULTS: Showing {base_query_name} results {delivery_info['current_start']}-{delivery_info['current_end']} of {total_nodes} total results (batch {batch_num}/{len(batches)})"

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

            code_content = result_dict.get("code_snippet", "")
            if code_content:
                # Parse line information
                lines = result_dict.get("lines")
                start_line = None
                if lines:
                    if isinstance(lines, str):
                        import json

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

                # Apply line filtering for GET_CODE_FROM_FILE_LINES query
                line_filtered = False
                if query_name == "GET_CODE_FROM_FILE_LINES":
                    requested_start_line = final_params.get("start_line")
                    requested_end_line = final_params.get("end_line")

                    # Ensure line numbers are integers
                    if requested_start_line is not None:
                        try:
                            requested_start_line = int(requested_start_line)
                        except (ValueError, TypeError):
                            requested_start_line = None
                    if requested_end_line is not None:
                        try:
                            requested_end_line = int(requested_end_line)
                        except (ValueError, TypeError):
                            requested_end_line = None

                    filtered_result = process_code_with_line_filtering(
                        code_content,
                        file_start_line=start_line or 1,
                        start_line=requested_start_line,
                        end_line=requested_end_line,
                    )

                    code_content = filtered_result["code"]
                    start_line = filtered_result["actual_start_line"]
                    result_dict["lines"] = [
                        filtered_result["actual_start_line"],
                        filtered_result["actual_end_line"],
                    ]
                    # Update the code_snippet in result_dict with filtered content
                    result_dict["code_snippet"] = filtered_result["code"]
                    line_filtered = True

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
                        chunk_scenario = determine_guidance_scenario(
                            total_nodes=1,
                            include_code=True,
                            code_lines=len(code_lines),
                            chunk_info=chunk_info,
                        )

                        chunk_guidance = build_guidance_message(
                            search_type=SearchType.DATABASE,
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
                                "type": "database_query_chunk",
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

                    # For line-filtered queries, use the requested line range for guidance
                    if line_filtered and query_name == "GET_CODE_FROM_FILE_LINES":
                        requested_start_line = final_params.get("start_line")
                        requested_end_line = final_params.get("end_line")
                        if requested_start_line and requested_end_line:
                            # Ensure line numbers are integers for guidance
                            try:
                                guidance_params["start_line"] = int(
                                    requested_start_line
                                )
                                guidance_params["end_line"] = int(requested_end_line)
                            except (ValueError, TypeError):
                                # Fallback to actual result lines if conversion fails
                                result_lines = result_dict.get("lines")
                                if (
                                    result_lines
                                    and isinstance(result_lines, list)
                                    and len(result_lines) >= 2
                                ):
                                    try:
                                        guidance_params["start_line"] = int(
                                            result_lines[0]
                                        )
                                        guidance_params["end_line"] = int(
                                            result_lines[1]
                                        )
                                    except (ValueError, TypeError):
                                        pass
                        else:
                            # Fallback to actual result lines if requested lines not available
                            result_lines = result_dict.get("lines")
                            if (
                                result_lines
                                and isinstance(result_lines, list)
                                and len(result_lines) >= 2
                            ):
                                try:
                                    guidance_params["start_line"] = int(result_lines[0])
                                    guidance_params["end_line"] = int(result_lines[1])
                                except (ValueError, TypeError):
                                    pass
                    else:
                        # Check if we have line range information from the result
                        result_lines = result_dict.get("lines")
                        if result_lines:
                            if (
                                isinstance(result_lines, list)
                                and len(result_lines) >= 2
                            ):
                                try:
                                    guidance_params["start_line"] = int(result_lines[0])
                                    guidance_params["end_line"] = int(result_lines[1])
                                except (ValueError, TypeError):
                                    pass
                            elif isinstance(result_lines, str):
                                try:
                                    lines_data = json.loads(result_lines)
                                    if (
                                        isinstance(lines_data, list)
                                        and len(lines_data) >= 2
                                    ):
                                        guidance_params["start_line"] = int(
                                            lines_data[0]
                                        )
                                        guidance_params["end_line"] = int(lines_data[1])
                                except (json.JSONDecodeError, ValueError, TypeError):
                                    pass

                    # Use shared guidance function with line-filtering parameters
                    guidance_message = build_batch_guidance_message(
                        search_type=SearchType.DATABASE,
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
                missing_content_guidance = build_guidance_message(
                    search_type=SearchType.DATABASE,
                    scenario=GuidanceScenario.NODE_MISSING_CODE_CONTENT,
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

                code_content = result_dict.get("code_snippet", "")
                if code_content:
                    # Parse line information
                    lines = result_dict.get("lines")
                    start_line = None
                    if lines:
                        if isinstance(lines, str):
                            import json

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

                    # Apply line filtering for GET_CODE_FROM_FILE_LINES query
                    line_filtered = False
                    if query_name == "GET_CODE_FROM_FILE_LINES":
                        requested_start_line = final_params.get("start_line")
                        requested_end_line = final_params.get("end_line")

                        # Ensure line numbers are integers
                        if requested_start_line is not None:
                            try:
                                requested_start_line = int(requested_start_line)
                            except (ValueError, TypeError):
                                requested_start_line = None
                        if requested_end_line is not None:
                            try:
                                requested_end_line = int(requested_end_line)
                            except (ValueError, TypeError):
                                requested_end_line = None

                        filtered_result = process_code_with_line_filtering(
                            code_content,
                            file_start_line=start_line or 1,
                            start_line=requested_start_line,
                            end_line=requested_end_line,
                        )

                        code_content = filtered_result["code"]
                        start_line = filtered_result["actual_start_line"]
                        result_dict["lines"] = [
                            filtered_result["actual_start_line"],
                            filtered_result["actual_end_line"],
                        ]
                        # Update the code_snippet in result_dict with filtered content
                        result_dict["code_snippet"] = filtered_result["code"]
                        line_filtered = True

                    code_lines = code_content.split("\n")

                    if (
                        should_chunk_content(
                            code_content, SEARCH_CONFIG["chunking_threshold"]
                        )
                        and not line_filtered
                    ):
                        # Handle chunking for this node directly
                        # For sequential processing, this is the last node if it's the last in the result set
                        is_last_node = i == total_nodes

                        chunks = chunk_large_code_clean(
                            code_content,
                            file_start_line=start_line or 1,
                            max_lines=SEARCH_CONFIG["chunk_size"],
                        )

                        for chunk in chunks:
                            chunk_info = create_chunk_info(chunk)

                            # Build sequential node guidance message
                            sequential_scenario = determine_sequential_node_scenario(
                                chunk_info=chunk_info,
                            )

                            chunk_guidance = build_sequential_node_message(
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
                                    "type": "database_query_node",
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
                        sequential_scenario = determine_sequential_node_scenario()

                        node_guidance = build_sequential_node_message(
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
                                "type": "database_query_node",
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
                    from src.services.agent.agent_prompt.guidance_builder import (
                        SequentialNodeScenario,
                    )

                    sequential_scenario = SequentialNodeScenario.NODE_NO_CODE_CONTENT

                    node_guidance = build_sequential_node_message(
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
                            "type": "database_query_node",
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
            "type": "database_query_error",
            "tool_name": "database",
            "query_name": query_name,
            "query": action.parameters,
            "error": error_msg,
            "include_code": code_snippet,
        }


def execute_database_action(
    action: AgentAction, db_connection=None
) -> Iterator[Dict[str, Any]]:
    logger.debug(f"🔍 Database action triggered with parameters: {action.parameters}")
    if action.parameters and "query_name" in action.parameters:
        yield from execute_structured_database_query(action, db_connection)
        return

    yield {
        "type": "database_query_error",
        "tool_name": "database",
        "query_name": "unknown",
        "query": action.parameters or {},
        "error": "Database action requires 'query_name' parameter",
        "include_code": False,
    }
