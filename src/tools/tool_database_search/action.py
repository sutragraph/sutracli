from loguru import logger
from typing import Iterator, Dict, Any, List, Optional
from graph.sqlite_client import SQLiteConnection
from services.agent.delivery_management import delivery_manager
from services.agent.agent_prompt.guidance_builder import (
    determine_semantic_batch_scenario,
    build_guidance_message,
    SearchType,
)
from tools.utils import (
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
from tools.utils.search_utils import (
    build_batch_guidance_message,
)
from services.agent_connection_enhancer import (
    get_agent_connection_enhancer,
)
from queries.agent_queries import (
    GET_NODES_BY_EXACT_NAME,
    GET_NODES_BY_NAME_LIKE,
    GET_NODES_BY_KEYWORD_SEARCH,
    GET_CODE_FROM_FILE,
    GET_ALL_NODE_NAMES_FROM_FILE,
    GET_FUNCTION_CALLERS,
    GET_FUNCTION_CALLEES,
    GET_FILE_DEPENDENCIES,
)
from services.agent.agent_prompt.guidance_builder import (
    GuidanceScenario,
)
import os
from models.agent import AgentAction
from services.agent.agent_prompt.guidance_builder import (
    SearchType,
    determine_guidance_scenario,
    determine_sequential_node_scenario,
    build_guidance_message,
    build_sequential_node_message,
)
from tools.utils.constants import (
    SEARCH_CONFIG,
    DATABASE_QUERY_CONFIG,
    DATABASE_ERROR_GUIDANCE,
    DELIVERY_QUEUE_CONFIG,
    GUIDANCE_MESSAGES,
)
from services.agent.delivery_management import delivery_manager
from tools.utils.search_utils import (
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


def _add_connection_information(
    results: List[Dict[str, Any]],
    project_id: Optional[int] = None,
    context: str = "agent",
) -> str:
    """
    Add connection information to database query results for agent service only.

    Args:
        results: Database query results
        db_connection: Database connection
        project_id: Optional project ID
        context: Context of the call ("agent" or "cross_index")

    Returns:
        Formatted connection information string (empty if context is not "agent")
    """
    try:
        if not results or context != "agent":
            return ""

        # Get agent connection enhancer
        connection_enhancer = get_agent_connection_enhancer()

        # Enhance results with connection information
        formatted_connections = connection_enhancer.enhance_database_results(
            results, project_id, context
        )

        return formatted_connections

    except Exception as e:
        logger.error(f"Error adding connection information: {e}")
        return ""


def execute_structured_database_query(
    action: AgentAction, context: str = "agent"
) -> Iterator[Dict[str, Any]]:
    # Initialize variables for exception handling
    query_name = action.parameters.get("query_name", "unknown")
    code_snippet = action.parameters.get("code_snippet", True)

    try:
        # Get database connection from singleton
        db_connection = SQLiteConnection()

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
                from pathlib import Path
                import os

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

                # If still no results, try case-insensitive fallback
                if not filename_fallback_results:
                    logger.debug(
                        f"🔄 Trying case-insensitive fallback for filename: {filename}"
                    )

                    # Try case-insensitive search by looking for files with similar names
                    case_insensitive_cursor = db_connection.connection.cursor()
                    case_insensitive_query = """
                        SELECT
                            n.node_id,
                            n.node_type,
                            n.name,
                            n.lines,
                            n.code_snippet,
                            n.properties,
                            fh.file_path,
                            fh.language,
                            fh.file_size,
                            p.name as project_name,
                            p.id as project_id
                        FROM nodes n
                        LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
                        LEFT JOIN projects p ON n.project_id = p.id
                        WHERE LOWER(n.name) = LOWER(:name)
                        AND n.node_type = 'File'
                        AND (:project_id IS NULL OR n.project_id = :project_id)
                        ORDER BY n.node_id
                        LIMIT 10
                    """
                    case_insensitive_cursor.execute(
                        case_insensitive_query, filename_fallback_params
                    )
                    case_insensitive_columns = (
                        [
                            description[0]
                            for description in case_insensitive_cursor.description
                        ]
                        if case_insensitive_cursor.description
                        else []
                    )
                    case_insensitive_rows = case_insensitive_cursor.fetchall()
                    filename_fallback_results = [
                        dict(zip(case_insensitive_columns, row))
                        for row in case_insensitive_rows
                    ]

                    if filename_fallback_results:
                        logger.debug(
                            f"✅ Case-insensitive fallback found {len(filename_fallback_results)} results"
                        )
                    else:
                        logger.debug(
                            "❌ Case-insensitive fallback also returned 0 results"
                        )

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

                    # Add connection information to the last chunk if available
                    if all_delivery_items:
                        connection_info = _add_connection_information(
                            [result_dict], current_project_id, context
                        )
                        if connection_info:
                            last_item = all_delivery_items[-1]
                            last_item["data"] += "\n\n" + connection_info

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

                    # Add connection information for single result
                    connection_info = _add_connection_information(
                        [result_dict], current_project_id, context
                    )

                    # Send single batch result for small files
                    result_data = (
                        guidance_message + "\n\n" + beautified_result
                        if guidance_message
                        else beautified_result
                    )

                    # Append connection information if available
                    if connection_info:
                        result_data += "\n\n" + connection_info

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

                # Add connection information for single result without code
                connection_info = _add_connection_information(
                    [result_dict], current_project_id, context
                )

                # Send single batch result for missing code
                result_data = guidance_message + beautified_result

                # Append connection information if available
                if connection_info:
                    result_data += "\n\n" + connection_info

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
                    from services.agent.agent_prompt.guidance_builder import (
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

            # Add connection information to all delivery items before registering
            if all_delivery_items:
                # Get connection information for all results
                connection_info = _add_connection_information(
                    results, current_project_id, context
                )

                # Add connection information to the last delivery item if available
                if connection_info and all_delivery_items:
                    last_item = all_delivery_items[-1]
                    last_item["data"] += "\n\n" + connection_info

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


def register_and_deliver_first_batch(
    action_type: str,
    action_parameters: Dict[str, Any],
    delivery_items: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Register delivery queue and get first batch of items for semantic search.

    Args:
        action_type: Type of action (should be "semantic_search")
        action_parameters: Action parameters
        delivery_items: List of items to register for delivery

    Returns:
        First batch of items from delivery queue or None if no items
    """
    if not delivery_items:
        return None

    # Register all items with delivery manager
    delivery_manager.register_delivery_queue(
        action_type, action_parameters, delivery_items
    )

    # Get batch size for semantic search
    batch_size = DELIVERY_QUEUE_CONFIG.get("semantic_search", 10)

    # Collect first batch of items
    batch_items = []
    for _ in range(batch_size):
        next_item = delivery_manager.get_next_item(action_type, action_parameters)
        if next_item:
            batch_items.append(next_item)
        else:
            break  # No more items available

    if not batch_items:
        return None

    # Combine batch items into a single response
    total_nodes = delivery_items[0].get("total_nodes", len(delivery_items))
    query = action_parameters.get("query", "")

    # Calculate delivery info
    delivered_count = len(batch_items)
    remaining_count = len(delivery_items) - delivered_count

    # Add semantic search guidance
    guidance_message = ""
    if action_type == "semantic_search":
        scenario = determine_semantic_batch_scenario()

        guidance_message = build_guidance_message(
            search_type=SearchType.SEMANTIC,
            scenario=scenario,
            total_nodes=total_nodes,
            delivered_count=delivered_count,
            remaining_count=remaining_count,
            batch_number=1,  # This is always the first batch
        )

        if guidance_message:
            guidance_message += "\n\n"

    # Combine all data from batch items
    combined_data = []
    for item in batch_items:
        combined_data.append(item.get("data", ""))

    # Combine guidance with data
    final_data = guidance_message + "\n\n".join(combined_data)

    return {
        "type": "tool_use",
        "tool_name": "semantic_search",
        "query": query,
        "result": f"result found: {total_nodes}",
        "data": final_data,
        "code_snippet": True,
        "total_nodes": total_nodes,
        "batch_info": {
            "delivered_count": delivered_count,
            "remaining_count": remaining_count,
            "batch_size": batch_size,
        },
    }


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
