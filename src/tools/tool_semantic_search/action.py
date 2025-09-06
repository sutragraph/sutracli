from embeddings.vector_store import VectorStore
from loguru import logger
from typing import Iterator, Dict, Any, List, Optional
from embeddings import get_vector_store
from graph.graph_operations import GraphOperations
from graph.sqlite_client import SQLiteConnection
from models.agent import AgentAction
from tools.utils.constants import (
    SEMANTIC_SEARCH_CONFIG,
)


from tools.utils.enriched_context_formatter import (
    beautify_enriched_context_auto,
    format_chunk_with_enriched_context,
)


def _perform_vector_search(
    vector_store: VectorStore, query: str, project_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Perform vector database search with chunk-specific results."""
    config = SEMANTIC_SEARCH_CONFIG
    limit = config["total_nodes_limit"]

    logger.debug(
        f"Semantic search: fetching {limit} chunk-specific nodes with code snippets"
    )

    return vector_store.search_similar_chunks(
        query,
        limit=limit,
        threshold=config["similarity_threshold"],
        project_id=project_id,
    )


def _get_enriched_context(
    graph_ops: GraphOperations, node_id: str
) -> Optional[Dict[str, Any]]:
    """Get enriched context for a node using graph operations."""
    try:
        if node_id.startswith("block_"):
            block_id = int(node_id.split("_")[1])
            return graph_ops.get_enriched_block_context(block_id)
        elif node_id.startswith("file_"):
            file_id = int(node_id.split("_")[1])
            return graph_ops.get_enriched_file_context(file_id)
        else:
            logger.warning(f"Unknown node_id format: {node_id}")
            return None
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing node_id {node_id}: {e}")
        return None


def _get_block_total_lines(enriched_context: Dict[str, Any]) -> int:
    """Get total number of lines in a block from enriched context."""
    if "block" not in enriched_context:
        return 0

    block_data = enriched_context["block"]
    content = block_data.get("content", "")
    if not content:
        return 0

    return len(content.split("\n"))


def _extract_chunk_specific_code(
    enriched_context: Dict[str, Any],
    chunk_start_line: Optional[int],
    chunk_end_line: Optional[int],
) -> str:
    """Extract chunk-specific code from enriched file context."""
    # Get content from file (blocks now use full context display)
    if "file" not in enriched_context:
        return ""

    file_data = enriched_context["file"]
    content = file_data.get("content", "")
    node_start_line = 1

    if not content:
        return ""

    if not chunk_start_line or not chunk_end_line:
        return content  # Return full content if no chunk boundaries

    try:
        # Calculate relative line positions within the content
        relative_start = max(
            0, (chunk_start_line or 1) - (node_start_line or 1)
        )
        relative_end = (chunk_end_line or 1) - (node_start_line or 1) + 1

        code_lines = content.split("\n")

        if (
            relative_start < len(code_lines)
            and relative_start >= 0
            and relative_end > relative_start
            and relative_end <= len(code_lines)
        ):
            # Extract only the lines that belong to this chunk
            chunk_lines = code_lines[relative_start:relative_end]
            return "\n".join(chunk_lines)
        else:
            # If chunk boundaries don't align, return full content
            return content

    except (IndexError, TypeError):
        return content  # Fallback to full content


def _deduplicate_block_results(
    vector_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Deduplicate multiple chunks from the same block, keeping the highest
    similarity result. Files are not deduplicated since they represent
    different content chunks.
    """
    # Separate blocks and files
    block_results = {}
    file_results = []
    other_results = []

    for result in vector_results:
        node_id = result.get("node_id", "")

        if node_id.startswith("block_"):
            # Extract base block_id (could be block_123 or block_123_chunk_0)
            block_id = node_id.split("_")[1] if "_" in node_id else node_id
            similarity = result.get("similarity", 0.0)

            # Keep only the best result for each block
            if block_id not in block_results or similarity > block_results[
                block_id
            ].get("similarity", 0.0):
                block_results[block_id] = result
        elif node_id.startswith("file_"):
            # Keep all file results (different chunks are meaningful)
            file_results.append(result)
        else:
            # Keep other types as-is
            other_results.append(result)

    # Combine deduplicated results
    deduplicated = (
        list(block_results.values()) + file_results + other_results
    )

    # Sort by similarity to maintain quality order
    deduplicated.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)

    return deduplicated


def _process_sequential_chunk_results(
    vector_results: List[Dict[str, Any]],
    query: str,
    action_parameters: Dict[str, Any],
    project_name: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    """Process chunk-specific results for sequential sending."""

    # Deduplicate block results to avoid showing the same block multiple times
    # when multiple chunks from the same block match the search
    deduplicated_results = _deduplicate_block_results(vector_results)
    total_nodes = len(deduplicated_results)

    # Process results for delivery
    graph_ops = GraphOperations()

    for i, result in enumerate(deduplicated_results, 1):
        # Get enriched context using graph operations
        enriched_context = _get_enriched_context(graph_ops, result["node_id"])

        if enriched_context:
            # Extract chunk information
            chunk_start_line = result.get("chunk_start_line")
            chunk_end_line = result.get("chunk_end_line")
            use_chunk = False  # Initialize for all branches

            # Check if this is a code block vs unsupported file based on node_id
            if result["node_id"].startswith("block_"):
                # For code blocks: Check block size against threshold
                block_total_lines = _get_block_total_lines(enriched_context)
                block_chunk_threshold = SEMANTIC_SEARCH_CONFIG[
                    "block_chunk_threshold"
                ]

                logger.debug(
                    f"Block {result['node_id']}: {block_total_lines} lines "
                    f"(threshold: {block_chunk_threshold})"
                )

                # Initialize the default to using full block
                reason = "small block or chunking not possible"
                chunk_data = ""  # Initialize chunk_data

                # Check if we should try to use chunk
                if (
                    block_total_lines > block_chunk_threshold
                    and chunk_start_line and chunk_end_line
                    and "block" in enriched_context
                    and enriched_context["block"].get("content")
                ):

                    # Extract the chunk from the block content
                    block_content = enriched_context["block"]["content"]
                    block_start_line = enriched_context["block"].get(
                        "start_line", 1
                    )

                    # Calculate relative position within the block
                    relative_start = max(0, (chunk_start_line - block_start_line))
                    relative_end = (chunk_end_line - block_start_line) + 1

                    # Extract the chunk from the block content
                    content_lines = block_content.split("\n")

                    # Only use chunk if boundaries are valid
                    if (
                        relative_start < len(content_lines)
                        and relative_end <= len(content_lines)
                    ):
                        chunk_lines = content_lines[relative_start:relative_end]
                        chunk_data = "\n".join(chunk_lines)
                        use_chunk = True
                    else:
                        reason = "chunk extraction failed"

                # Format the result based on whether we're using chunk or full block
                if use_chunk and chunk_start_line is not None and chunk_end_line is not None:
                    logger.debug(
                        f"Using chunk for large block {result['node_id']} "
                        f"(lines {chunk_start_line}-{chunk_end_line})"
                    )
                    beautified_result = format_chunk_with_enriched_context(
                        enriched_context,
                        chunk_start_line,
                        chunk_end_line,
                        chunk_data,
                        i,
                        total_nodes,
                        node_id=result["node_id"],
                    )
                else:
                    logger.debug(
                        f"Using full block for {result['node_id']} ({reason})"
                    )
                    beautified_result = beautify_enriched_context_auto(
                        enriched_context,
                        i,
                        include_code=True,
                        total_nodes=total_nodes,
                        node_id=result["node_id"],
                    )
            elif (
                result["node_id"].startswith("file_")
                and chunk_start_line is not None
                and chunk_end_line is not None
            ):
                # For unsupported files: Use chunking since we have no logical structure
                chunk_code = _extract_chunk_specific_code(
                    enriched_context, chunk_start_line, chunk_end_line
                )

                if chunk_code:
                    # Format with chunk-specific context for files
                    beautified_result = format_chunk_with_enriched_context(
                        enriched_context,
                        chunk_start_line,
                        chunk_end_line,
                        chunk_code,
                        i,
                        total_nodes,
                        node_id=result["node_id"],
                    )
                else:
                    # No chunk code available, use full context
                    beautified_result = beautify_enriched_context_auto(
                        enriched_context,
                        i,
                        include_code=True,
                        total_nodes=total_nodes,
                        node_id=result["node_id"],
                    )
            else:
                # No chunk boundaries or unknown type, use full context
                beautified_result = beautify_enriched_context_auto(
                    enriched_context,
                    i,
                    include_code=True,
                    total_nodes=total_nodes,
                    node_id=result["node_id"],
                )

            # Yield processed result for delivery system to handle batching
            yield {
                "type": "tool_use",
                "tool_name": "semantic_search",
                "query": query,
                "result": f"Found {len(deduplicated_results)} nodes",
                "node_index": i,
                "total_nodes": total_nodes,
                "data": beautified_result,
                "code_snippet": True,
                "node_id": result["node_id"],
                "project_name": project_name,
                "chunk_info": {
                    "start_line": chunk_start_line,
                    "end_line": chunk_end_line,
                    "similarity": result.get("similarity", 0.0),
                    "block_total_lines": (
                        _get_block_total_lines(enriched_context)
                        if result["node_id"].startswith("block_")
                        else None
                    ),
                    "used_chunking": (
                        use_chunk if result["node_id"].startswith("block_") else False
                    ),
                },
            }
        else:
            # Handle missing enriched context
            yield {
                "type": "tool_use",
                "tool_name": "semantic_search",
                "query": query,
                "node_index": i,
                "total_nodes": total_nodes,
                "data": (
                    f"❌ Node {i}/{total_nodes}: "
                    f"Could not retrieve enriched context for {result['node_id']}."
                ),
                "code_snippet": True,
                "node_id": result["node_id"],
                "project_name": project_name,
            }

    if not deduplicated_results:
        # No results to return - send completion signal
        no_results_msg = "No deliverable items found."

        yield {
            "tool_name": "semantic_search",
            "type": "tool_use",
            "query": query,
            "result": f"Found {len(deduplicated_results)} nodes",
            "data": no_results_msg,
            "code_snippet": True,
            "total_nodes": total_nodes,
            "project_name": project_name,
        }


def execute_semantic_search_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    logger.debug(f"Executing semantic search action: {action}")

    try:
        project_name = action.parameters.get("project_name")
        query = action.parameters.get("query", "")

        # Convert project_name to project_id if provided
        project_id = None
        if project_name:
            db_connection = SQLiteConnection()
            project = db_connection.get_project(project_name)
            if project:
                project_id = project.id
                yield {
                    "type": "info",
                    "message": f"Searching in project: {project_name}",
                    "tool_name": "semantic_search",
                    "project_name": project_name,
                }
            else:
                raise Exception(f"Project '{project_name}' not found")

        # Initialize vector store
        vector_store = get_vector_store()

        # Perform search using helper function
        vector_results = _perform_vector_search(vector_store, query, project_id)
        total_nodes = len(vector_results)

        # Handle empty results
        if total_nodes == 0:
            no_results_msg = "No results found for the query."

            yield {
                "tool_name": "semantic_search",
                "type": "tool_use",
                "query": query,
                "result": f"Found {total_nodes} nodes",
                "code_snippet": True,
                "total_nodes": total_nodes,
                "data": no_results_msg,
                "project_name": project_name,
            }
            return

        # Process results and yield them for delivery system to handle
        # The delivery system will handle batching according to DELIVERY_QUEUE_CONFIG
        yield from _process_sequential_chunk_results(
            vector_results,
            query,
            action.parameters,
            project_name,
        )
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        yield {
            "tool_name": "semantic_search",
            "type": "tool_error",
            "error": f"Semantic search failed: {str(e)}",
            "project_name": action.parameters.get("project_name"),
        }
