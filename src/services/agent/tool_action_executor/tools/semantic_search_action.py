from loguru import logger
from typing import Iterator, Dict, Any, List
from src.embeddings.vector_db import VectorDatabase
from src.services.agent.tool_action_executor.utils import (
    get_node_details,
    beautify_node_result,
)
from src.services.agent.agentic_core import AgentAction
from src.services.agent.agent_prompt.guidance_builder import (
    SearchType,
    build_guidance_message,
)
from src.services.agent.tool_action_executor.utils.constants import (
    SEMANTIC_SEARCH_CONFIG,
    DELIVERY_QUEUE_CONFIG,
)
from src.services.agent.delivery_management import delivery_manager

def _extract_search_parameters(action: AgentAction) -> str:
    """Extract query parameter from action."""
    query = (
        action.query or action.parameters.get("query", "") if action.parameters else ""
    )
    if not query and action.description:
        query = (
            action.description.lower().replace("find ", "").replace("search for ", "")
        )

    return query


def _perform_vector_search(
    vector_db: VectorDatabase, query: str, project_id=None
) -> List[Dict[str, Any]]:
    """Perform vector database search with chunk-specific results."""
    config = SEMANTIC_SEARCH_CONFIG
    limit = config["total_nodes_limit"]

    logger.debug(
        f"Semantic search: fetching {limit} chunk-specific nodes with code snippets"
    )

    return vector_db.search_similar_chunks(
        query, limit=limit, threshold=config["similarity_threshold"], project_id=project_id
    )


def _process_sequential_chunk_results(
    vector_results: List[Dict[str, Any]],
    query: str,
    action_parameters: Dict[str, Any],
    db_connection=None,
) -> Iterator[Dict[str, Any]]:
    """Process chunk-specific results for sequential sending via delivery queue."""
    total_nodes = len(vector_results)

    # Check if we have a pending delivery for this query
    next_item = delivery_manager.get_next_item("semantic_search", action_parameters)

    if next_item is not None:
        # We have a pending item from a previous call - deliver it
        yield next_item
        return

    # No pending delivery - collect all chunk items and register them
    all_delivery_items = []

    for i, result in enumerate(vector_results, 1):
        node_details = get_node_details(
            result["node_id"], result.get("project_id", None), db_connection
        )
        if node_details:
            # Extract chunk-specific code using the same logic as search_chunks_with_code
            chunk_code = _extract_chunk_specific_code(node_details, result)

            if chunk_code:
                # Create a modified node_details with only the chunk-specific code
                chunk_node_details = node_details.copy()
                chunk_node_details["code_snippet"] = chunk_code

                # Update lines information to reflect chunk boundaries
                chunk_start_line = result.get("chunk_start_line")
                chunk_end_line = result.get("chunk_end_line")
                if chunk_start_line and chunk_end_line:
                    import json

                    chunk_node_details["lines"] = json.dumps(
                        [chunk_start_line, chunk_end_line]
                    )

                # Format the result using existing beautify function
                beautified_result = beautify_node_result(
                    chunk_node_details,
                    i,
                    include_code=True,
                    total_nodes=total_nodes,
                )

                # Collect item for delivery manager
                all_delivery_items.append(
                    {
                        "type": "tool_use",
                        "tool_name": "semantic_search",
                        "query": query,
                        "result": f"Found {len(vector_results)} nodes",
                        "node_index": i,
                        "total_nodes": total_nodes,
                        "data": beautified_result,
                        "code_snippet": True,  # Always true for semantic search
                    }
                )
            else:
                # No code content available
                beautified_result = beautify_node_result(
                    node_details, i, include_code=True, total_nodes=total_nodes
                )

                all_delivery_items.append(
                    {
                        "type": "tool_use",
                        "tool_name": "semantic_search",
                        "query": query,
                        "node_index": i,
                        "total_nodes": total_nodes,
                        "data": f"Node {i}: No code content available for this chunk.",
                        "code_snippet": True,
                    }
                )
        else:
            # Handle missing node details
            all_delivery_items.append(
                {
                    "type": "tool_use",
                    "tool_name": "semantic_search",
                    "query": query,
                    "node_index": i,
                    "total_nodes": total_nodes,
                    "data": f"Node {i}: Node details not found.",
                    "code_snippet": True,
                }
            )

    # Register all items with delivery manager and send first batch
    if all_delivery_items:
        from src.services.agent.tool_action_executor.utils.delivery_utils import (
            register_and_deliver_first_batch,
        )

        first_batch = register_and_deliver_first_batch(
            "semantic_search", action_parameters, all_delivery_items
        )
        if first_batch:
            yield first_batch
    else:
        # No items to deliver - send completion signal
        yield {
            "tool_name": "semantic_search",
            "type": "tool_use",
            "query": query,
            "result": f"Found {len(vector_results)} nodes",
            "data": f"No deliverable items found.",
            "code_snippet": True,
            "total_nodes": total_nodes,
        }


def _extract_chunk_specific_code(
    node_details: Dict[str, Any], result: Dict[str, Any]
) -> str:
    """Extract only the chunk-specific lines from the node code, similar to search_chunks_with_code."""
    code_snippet = node_details.get("code_snippet", "")
    if not code_snippet:
        return ""

    chunk_start_line = result.get("chunk_start_line")
    chunk_end_line = result.get("chunk_end_line")

    if not chunk_start_line or not chunk_end_line:
        return code_snippet  # Return full code if no chunk boundaries

    # Parse node lines to get the node's starting line
    node_lines = node_details.get("lines")
    if node_lines:
        import json

        try:
            lines_data = json.loads(node_lines)
            if isinstance(lines_data, list) and len(lines_data) >= 1:
                node_start_line = lines_data[0]

                # Calculate relative line positions within the code
                relative_start = max(0, chunk_start_line - node_start_line)
                relative_end = chunk_end_line - node_start_line + 1

                code_lines = code_snippet.split("\n")

                if (
                    relative_start < len(code_lines)
                    and relative_start >= 0
                    and relative_end > relative_start
                    and relative_end <= len(code_lines)
                ):
                    # Extract only the lines that belong to this chunk
                    chunk_lines = code_lines[relative_start:relative_end]

                    # Add line numbers to the chunk code
                    from src.services.agent.tool_action_executor.utils.code_processing_utils import (
                        add_line_numbers_to_code,
                    )

                    return add_line_numbers_to_code(
                        "\n".join(chunk_lines), chunk_start_line
                    )
        except (json.JSONDecodeError, IndexError, TypeError):
            pass

    return code_snippet  # Fallback to full code


def execute_semantic_search_action(
    action: AgentAction, vector_db=None, db_connection=None, project_id=None
) -> Iterator[Dict[str, Any]]:
    logger.debug(f"Executing semantic search action: {action}")

    try:
        # Check if this is a fetch_next_code request (handles batch delivery)
        if action.parameters.get("fetch_next_code", False):
            logger.debug("🔄 Fetch next batch request detected")

            batch_size = DELIVERY_QUEUE_CONFIG.get("semantic_search", 7)

            # Only use existing delivery queue if NO query is provided (just fetch_next_code)
            # If query is provided along with fetch_next_code, treat it as a new query
            if not action.parameters.get("query"):
                logger.debug(
                    "🔄 No query provided - using existing delivery queue for fetch_next_code"
                )
                # Get next batch of items
                batch_items = []
                for _ in range(batch_size):
                    next_item = delivery_manager.get_next_item_from_existing_queue()
                    if next_item:
                        batch_items.append(next_item)
                    else:
                        break
            else:
                logger.debug(
                    "🔄 Query provided with fetch_next_code - treating as new query"
                )
                # Get next batch of items
                batch_items = []
                for _ in range(batch_size):
                    next_item = delivery_manager.get_next_item(
                        "semantic_search", action.parameters
                    )
                    if next_item:
                        batch_items.append(next_item)
                    else:
                        break

            if batch_items:
                # Get total nodes from first item
                total_nodes = batch_items[0].get("total_nodes", 0)
                delivered_count = len(batch_items)

                # Get accurate remaining count from delivery manager queue status
                queue_status = delivery_manager.get_queue_status(
                    "semantic_search", action.parameters
                )
                remaining_count = (
                    queue_status.get("remaining_items", 0)
                    if queue_status.get("exists", False)
                    else 0
                )

                # Add guidance for fetch_next_code batch
                guidance_message = ""
                from src.services.agent.agent_prompt.guidance_builder import (
                    determine_semantic_batch_scenario,
                )

                # Calculate batch number based on current position
                current_position = (
                    queue_status.get("current_position", 0)
                    if queue_status.get("exists", False)
                    else 0
                )
                batch_number = max(1, (current_position // batch_size) + 1)

                scenario = determine_semantic_batch_scenario()

                guidance_message = build_guidance_message(
                    search_type=SearchType.SEMANTIC,
                    scenario=scenario,
                    total_nodes=total_nodes,
                    delivered_count=delivered_count,
                    remaining_count=remaining_count,
                    batch_number=batch_number,
                )

                if guidance_message:
                    guidance_message += "\n\n"

                # Combine batch items into a single response
                combined_data = []
                for item in batch_items:
                    combined_data.append(item.get("data", ""))

                # Combine guidance with data
                final_data = guidance_message + "\n\n".join(combined_data)

                yield {
                    "tool_name": "semantic_search",
                    "type": "tool_use",
                    "query": batch_items[0].get("query", "fetch_next_code"),
                    "result": f"Found {total_nodes} nodes",
                    "data": final_data,
                    "code_snippet": True,
                    "total_nodes": total_nodes,
                    "batch_info": {
                        "delivered_count": delivered_count,
                        "remaining_count": remaining_count,
                        "batch_size": batch_size,
                    },
                }
                return
            else:
                # No more items available
                yield {
                    "tool_name": "semantic_search",
                    "type": "tool_use",
                    "query": action.parameters.get("query", "fetch_next_code"),
                    "result": "result found: 0",
                    "data": "No more code chunks/nodes available. All items from the previous query have been delivered.",
                    "code_snippet": True,
                    "total_nodes": 0,
                }
                return

        # Extract parameters using helper function
        query = _extract_search_parameters(action)

        # Initialize vector database
        vector_db = vector_db or VectorDatabase()

        # Perform search using helper function
        vector_results = _perform_vector_search(vector_db, query, project_id)
        total_nodes = len(vector_results)

        # Yield tool usage information for logging
        yield {
            "tool_name": "semantic_search",
            "type": "tool_use",
            "query": query,
            "result": f"Found {total_nodes} nodes",
        }

        # Handle empty results case
        if total_nodes == 0:
            from src.services.agent.agent_prompt.guidance_builder import (
                GuidanceScenario,
            )

            guidance_message = build_guidance_message(
                search_type=SearchType.SEMANTIC,
                scenario=GuidanceScenario.NO_RESULTS_FOUND,
            )

            yield {
                "tool_name": "semantic_search",
                "type": "tool_use",
                "query": query,
                "result": "result found: 0",
                "data": guidance_message or "No results found for the query.",
                "code_snippet": True,  # Always true now
                "total_nodes": 0,
            }
            return

        # Always use sequential processing with delivery queue for semantic search
        yield from _process_sequential_chunk_results(
            vector_results,
            query,
            action.parameters,
            db_connection,
        )
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        yield {
            "tool_name": "semantic_search",
            "type": "semantic_search_error",
            "error": str(e),
        }
