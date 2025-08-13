"""
Tool Delivery Actions Factory

- Pattern: per-tool subclasses implement delivery batch functionality
- Usage: ActionExecutor asks factory for a delivery handler by tool name
- Centralizes all fetch_next_code and batch delivery logic
"""

from typing import Optional, Dict, Any, List
from loguru import logger
from services.agent.delivery_management import delivery_manager
from tools.guidance_builder import (
    enhance_semantic_search_event,
    enhance_database_search_event,
    calculate_database_batch_with_line_limit,
)

# Delivery queue configuration for different tool types
DELIVERY_QUEUE_CONFIG = {
    "database_metadata_only": 30,  # Nodes per batch for all other database queries without code
    "semantic_search": 15,  # Nodes per batch for semantic search (always with code)
}
from tools import ToolName


class BaseDeliveryAction:
    """Base class for tool-specific delivery actions."""

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_code requests for this tool."""
        return None

    def register_and_deliver_first_batch(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Register delivery queue and return first batch."""
        return None

    def check_pending_delivery(
        self, action_type: str, action_parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if there's a pending delivery for this query."""
        return None

    def get_batch_size(self) -> int:
        """Get the batch size for this tool."""
        return 15  # Default batch size

    def create_no_items_response(
        self,
        action_parameters: Dict[str, Any],
        total_results: int,
        include_code: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Create response when no deliverable items are found."""
        return None


class SemanticSearchDeliveryAction(BaseDeliveryAction):
    """Delivery actions for semantic search tool."""

    def get_batch_size(self) -> int:
        return DELIVERY_QUEUE_CONFIG.get("semantic_search", 15)

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_code requests for semantic search."""
        if not action.parameters.get("fetch_next_code", False):
            return None

        logger.debug("🔄 Fetch next request for semantic search")

        batch_size = self.get_batch_size()
        batch_items = []

        # Only use existing delivery queue if NO query is provided (just fetch_next_code)
        # If query is provided along with fetch_next_code, treat it as a new query
        if not action.parameters.get("query"):
            logger.debug(
                "🔄 No query provided - using existing delivery queue for fetch_next_code"
            )
            # Get next batch of items from existing queue
            for _ in range(batch_size):
                next_item = delivery_manager.get_next_item_from_existing_queue()
                if next_item:
                    batch_items.append(next_item)
                else:
                    break
        else:
            logger.debug("🔄 Query provided - treating as new query")
            # Get next batch of items with new query
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

            # Combine data from all items
            final_data = "\n\n".join(str(item.get("data", "")) for item in batch_items)

            event = {
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

            # Enhance with dynamic guidance
            return enhance_semantic_search_event(event, action.parameters)
        else:
            # No more items available
            return {
                "tool_name": "semantic_search",
                "type": "tool_use",
                "query": action.parameters.get("query", "fetch_next_code"),
                "result": "result found: 0",
                "data": "No more code chunks/nodes available. All items from the previous query have been delivered.",
                "code_snippet": True,
                "total_nodes": 0,
            }

    def register_and_deliver_first_batch(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Register delivery queue and get first batch for semantic search."""
        if not delivery_items:
            return None

        # Register all items with delivery manager
        delivery_manager.register_delivery_queue(
            action_type, action_parameters, delivery_items
        )

        # Get first batch
        batch_size = self.get_batch_size()
        batch_items = []

        for _ in range(batch_size):
            next_item = delivery_manager.get_next_item(action_type, action_parameters)
            if not next_item:
                break
            batch_items.append(next_item)

        if not batch_items:
            return None

        total_nodes = delivery_items[0].get("total_nodes", len(delivery_items))
        query = action_parameters.get("query", "")
        delivered_count = len(batch_items)
        # BUGFIX: Calculate remaining count correctly - use total_nodes, not delivery_items length
        remaining_count = total_nodes - delivered_count

        # Combine data from all items
        combined_data = "\n\n".join(str(item.get("data", "")) for item in batch_items)

        event = {
            "type": "tool_use",
            "tool_name": "semantic_search",
            "query": query,
            "result": f"result found: {total_nodes}",
            "data": combined_data,
            "code_snippet": True,
            "total_nodes": total_nodes,
            "batch_info": {
                "delivered_count": delivered_count,
                "remaining_count": remaining_count,
                "batch_size": batch_size,
            },
        }

        # Enhance with dynamic guidance
        return enhance_semantic_search_event(event, action_parameters)

    def create_no_items_response(
        self,
        action_parameters: Dict[str, Any],
        total_results: int,
        include_code: bool = True,
    ) -> Dict[str, Any]:
        """Create response when no deliverable items are found for semantic search."""
        query = action_parameters.get("query", "")
        return {
            "type": "tool_use",
            "tool_name": "semantic_search",
            "query": query,
            "code_snippet": include_code,
            "result": f"result found: {total_results}",
            "data": "No deliverable items found.",
            "total_nodes": total_results,
        }


class DatabaseSearchDeliveryAction(BaseDeliveryAction):
    """Delivery actions for database search tool."""

    def get_batch_size(self) -> int:
        # Default batch size for metadata-only queries
        return DELIVERY_QUEUE_CONFIG.get("database_metadata_only", 30)

    def get_batch_size_for_content(self, delivery_items: List[Dict[str, Any]]) -> int:
        """Get batch size based on content type."""
        # Check if any item has chunk_info (indicates chunked content)
        has_chunked_content = any(item.get("chunk_info") for item in delivery_items)

        if has_chunked_content:
            # For chunked content, deliver one chunk at a time
            return 1
        else:
            # For metadata-only content, use normal batch size
            return self.get_batch_size()

    def get_line_based_batch(
        self, delivery_items: List[Dict[str, Any]], line_limit: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Get batch of database items based on line limit.

        Args:
            delivery_items: List of items to batch
            line_limit: Maximum total lines allowed in batch

        Returns:
            List of items that fit within the line limit
        """
        return calculate_database_batch_with_line_limit(delivery_items, line_limit)

    def register_and_deliver_first_batch_with_line_limit(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
        line_limit: int = 500,
    ) -> Optional[Dict[str, Any]]:
        """Register delivery queue and get first batch with line limit for database search."""
        if not delivery_items:
            return None

        # Register all items with delivery manager
        logger.debug(f"📦 Registering {len(delivery_items)} items for {action_type}")

        delivery_manager.register_delivery_queue(
            action_type, action_parameters, delivery_items
        )

        # Debug: Check queue state after registration
        query_signature = delivery_manager._generate_query_signature(
            action_type, action_parameters
        )

        # Get line-based batch instead of fixed count batch
        logger.debug(
            f"📦 Getting batch from {len(delivery_items)} items with line_limit={line_limit}"
        )

        # BUGFIX: For chunked content, deliver only 1 chunk at a time regardless of line limit
        # This prevents all small chunks from being delivered in the first batch
        is_chunked_content = any(
            item.get("chunk_info")
            and item.get("chunk_info", {}).get("total_chunks", 1) > 1
            for item in delivery_items
        )

        if is_chunked_content:
            logger.debug("📦 Detected chunked content - delivering single chunk")
            # Sort chunks by chunk_num to ensure correct order
            sorted_chunks = sorted(
                delivery_items,
                key=lambda x: x.get("chunk_info", {}).get("chunk_num", 1),
            )
            line_based_batch = [sorted_chunks[0]] if sorted_chunks else []

            if sorted_chunks and sorted_chunks[0].get("chunk_info"):
                chunk_info = sorted_chunks[0]["chunk_info"]
                logger.debug(
                    f"📦 Delivering chunk {chunk_info.get('chunk_num', 1)}/{chunk_info.get('total_chunks', 1)}"
                )
        else:
            line_based_batch = self.get_line_based_batch(delivery_items, line_limit)

        if not line_based_batch:
            return None

        # Advance delivery queue position by the number of items in the line-based batch
        query_signature = delivery_manager._generate_query_signature(
            action_type, action_parameters
        )
        delivered_count = len(line_based_batch)
        old_position = delivery_manager._queue_positions.get(query_signature, 0)

        if query_signature in delivery_manager._queue_positions:
            delivery_manager._queue_positions[query_signature] = delivered_count
            logger.debug(
                f"📦 Advanced queue position from {old_position} to {delivered_count}"
            )
        else:
            logger.debug(
                f"❌ ERROR - Cannot advance position, query signature not found!"
            )

        # Calculate delivery statistics - handle chunked content properly
        # For chunked content, count unique files/nodes, not individual chunks
        unique_files = set()
        delivered_files = set()

        for item in delivery_items:
            # Use file path or node index to identify unique files
            file_key = item.get("file_path") or item.get(
                "node_index", item.get("data", "")[:50]
            )
            unique_files.add(file_key)

        for item in line_based_batch:
            file_key = item.get("file_path") or item.get(
                "node_index", item.get("data", "")[:50]
            )
            delivered_files.add(file_key)

        total_nodes = len(unique_files) if unique_files else len(delivery_items)
        delivered_nodes = (
            len(delivered_files) if delivered_files else len(line_based_batch)
        )
        remaining_nodes = total_nodes - delivered_nodes

        # Calculate line statistics - use chunk info if available for more accurate counts
        total_lines = 0
        delivered_lines = 0

        # For chunked content, use original file line counts from the delivered batch
        chunk_based_calculation = False
        if line_based_batch:
            for item in line_based_batch:
                chunk_info = item.get("chunk_info")
                if chunk_info:
                    chunk_based_calculation = True
                    # Use the original file lines from the delivered chunks, not all delivery items
                    total_lines = chunk_info.get("original_file_lines", 0)
                    break

        if chunk_based_calculation:
            # Use chunk info for accurate line counting
            for item in line_based_batch:
                chunk_info = item.get("chunk_info")
                if chunk_info:
                    delivered_lines += (
                        chunk_info.get("end_line", 0)
                        - chunk_info.get("start_line", 0)
                        + 1
                    )
        else:
            # Fallback to content-based line counting
            total_lines = sum(
                len(
                    str(item.get("data", "") or item.get("code_snippet", "")).split(
                        "\n"
                    )
                )
                for item in delivery_items
            )
            delivered_lines = sum(
                len(
                    str(item.get("data", "") or item.get("code_snippet", "")).split(
                        "\n"
                    )
                )
                for item in line_based_batch
            )

        # Combine data from batch items (clean any existing guidance first)
        cleaned_data_items = []
        guidance_found = False
        for item in line_based_batch:
            data = str(item.get("data", ""))
            # Remove any existing guidance messages that might have been added to individual items
            lines = data.split("\n")
            cleaned_lines = []
            skip_until_empty = False

            for line in lines:
                if line.startswith("Found ") and ("nodes" in line or "node" in line):
                    skip_until_empty = True
                    guidance_found = True
                    continue
                elif line.startswith("NOTE: There are more results"):
                    skip_until_empty = True
                    continue
                elif skip_until_empty and line.strip() == "":
                    skip_until_empty = False
                    continue
                elif not skip_until_empty:
                    cleaned_lines.append(line)

            cleaned_data = "\n".join(cleaned_lines).strip()
            if cleaned_data:
                cleaned_data_items.append(cleaned_data)

        combined_data = "\n\n".join(cleaned_data_items)

        event = {
            "type": "tool_use",
            "tool_name": "database",
            "query_name": action_parameters.get("query_name", "unknown"),
            "query": action_parameters,
            "result": f"found: {total_nodes}",
            "data": combined_data,
            "code_snippet": True,
            "total_nodes": total_nodes,
            "batch_info": {
                "delivered_count": delivered_nodes,
                "remaining_count": remaining_nodes,
                "delivered_lines": delivered_lines,
                "total_lines": total_lines,
            },
            "internal_delivery_handled": True,  # Flag to prevent duplicate delivery in executor
        }

        # Enhance with dynamic guidance
        delivery_context = {
            "is_batch": True,
            "remaining_nodes": remaining_nodes,
            "delivered_nodes": delivered_nodes,
            "total_lines": total_lines,
            "delivered_lines": delivered_lines,
        }

        # Add chunk_info if any of the delivery items has it
        if line_based_batch and line_based_batch[0].get("chunk_info"):
            # For multiple chunks in batch, calculate combined range
            first_chunk = line_based_batch[0].get("chunk_info")
            last_chunk = line_based_batch[-1].get("chunk_info")

            combined_chunk_info = {
                "start_line": first_chunk.get("start_line", 1),
                "end_line": last_chunk.get("end_line", first_chunk.get("end_line", 1)),
                "chunk_num": first_chunk.get("chunk_num", 1),
                "total_chunks": first_chunk.get("total_chunks", 1),
                "original_file_lines": first_chunk.get(
                    "original_file_lines", total_lines
                ),
            }
            delivery_context["chunk_info"] = combined_chunk_info

            # Override delivery_context values with chunk-based values for accurate guidance
            delivery_context["total_lines"] = combined_chunk_info["original_file_lines"]
            delivery_context["delivered_lines"] = (
                combined_chunk_info["end_line"] - combined_chunk_info["start_line"] + 1
            )

            # Override event total_nodes to 1 since chunks represent a single file
            event["total_nodes"] = 1

        return enhance_database_search_event(event, action_parameters, delivery_context)

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_code requests for database search."""
        if not action.parameters.get("fetch_next_code", False):
            return None
        logger.debug("🔄 Fetch next request for database search")

        # Use existing delivery queue if no query provided, or same query
        query_provided = action.parameters.get("query")

        if not query_provided:
            logger.debug("🔄 Using existing delivery queue for fetch_next_code")
            next_item = delivery_manager.get_next_item_from_existing_queue()
        else:
            # Check if this query matches the existing queue
            current_signature = delivery_manager._generate_query_signature(
                "database", action.parameters
            )

            if delivery_manager._last_query_signature == current_signature:
                logger.debug("🔄 Same query - using existing delivery queue")
                next_item = delivery_manager.get_next_item_from_existing_queue()
            else:
                logger.debug("🔄 Different query - treating as new query")
                next_item = delivery_manager.get_next_item(
                    "database", action.parameters
                )

        if next_item:

            # Format the response based on the original query type
            base_response = {
                "total_nodes": next_item.get("total_nodes", 1),
                "result": f"found: {next_item.get('total_nodes', 1)}",
                "code_snippet": next_item.get("code_snippet", True),
            }

            event = {
                "type": "tool_use",
                "tool_name": "database",
                "query_name": "fetch_next_code",
                "query": action.parameters,
                "data": next_item.get("data", ""),
                **base_response,
            }

            # Enhance with dynamic guidance for database
            delivery_context = {
                "is_batch": True,
                "remaining_nodes": 0,  # Will be calculated by delivery manager
                "delivered_nodes": 1,
                "chunk_info": next_item.get("chunk_info"),
            }
            return enhance_database_search_event(
                event, action.parameters, delivery_context
            )
        else:
            logger.debug(f"🔍 TRACE FETCH: ❌ *** NO NEXT ITEM AVAILABLE ***")

            # Debug final queue state
            if delivery_manager._last_query_signature:
                sig = delivery_manager._last_query_signature
                pos = delivery_manager._queue_positions.get(sig, 0)
                queue_len = len(delivery_manager._delivery_queues.get(sig, []))
                is_complete = delivery_manager._completed_deliveries.get(sig, False)
                logger.debug(
                    f"🔍 TRACE FETCH: Final queue state - pos: {pos}, len: {queue_len}, complete: {is_complete}"
                )

            # No more items available
            base_response = {
                "total_nodes": 0,
                "result": "query_complete",
                "code_snippet": True,
            }

            logger.debug(f"🔍 TRACE FETCH: *** RETURNING QUERY_COMPLETE ***")
            return {
                "type": "tool_use",
                "tool_name": "database",
                "query_name": "fetch_next_code",
                "query": action.parameters,
                "data": "No more code chunks available. All items from the previous query have been delivered.",
                **base_response,
            }

    def register_and_deliver_first_batch(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Register delivery queue and get first batch for database search."""
        if not delivery_items:
            return None

        # Register all items with delivery manager
        delivery_manager.register_delivery_queue(
            action_type, action_parameters, delivery_items
        )

        logger.debug(f"📦 Registered {len(delivery_items)} items for {action_type}")

        # For database search, find the item with actual content (not just status)
        # BUGFIX: For chunked content, always respect chunk order instead of selecting by data size

        # Check if this is chunked content
        is_chunked_content = any(
            item.get("chunk_info")
            and item.get("chunk_info", {}).get("total_chunks", 1) > 1
            for item in delivery_items
        )

        content_item = None
        if is_chunked_content:
            # Sort chunks by chunk_num to ensure correct order
            sorted_chunks = sorted(
                delivery_items,
                key=lambda x: x.get("chunk_info", {}).get("chunk_num", 1),
            )
            content_item = sorted_chunks[0]
            chunk_num = content_item.get("chunk_info", {}).get("chunk_num", 1)
            logger.debug(f"📦 Selected chunk {chunk_num} for delivery")
        else:
            # Original logic for non-chunked content
            for i, item in enumerate(delivery_items):
                # Look for the item that has substantial data content
                if item.get("data") and len(str(item.get("data", ""))) > 50:
                    content_item = item
                    break

        if not content_item:
            content_item = delivery_items[0]

        # Get the first item from the delivery manager to advance the queue
        next_item = delivery_manager.get_next_item(action_type, action_parameters)
        if next_item:
            # Update the content item with delivery metadata
            content_item.update(next_item)
            return content_item
        else:
            return content_item

    def check_pending_delivery(
        self, action_type: str, action_parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if there's a pending delivery for this query."""
        # If this is a fetch_next_code request, handle it as such
        if action_parameters.get("fetch_next_code", False):
            return self.handle_fetch_next(
                type("Action", (), {"parameters": action_parameters})()
            )

        # Otherwise, check if there's a pending delivery for a new query
        return delivery_manager.get_next_item(action_type, action_parameters)

    def create_no_items_response(
        self,
        action_parameters: Dict[str, Any],
        total_results: int,
        include_code: bool = True,
    ) -> Dict[str, Any]:
        """Create response when no deliverable items are found for database search."""
        query_name = action_parameters.get("query_name", "unknown")
        return {
            "type": "tool_use",
            "tool_name": "database",
            "query_name": query_name,
            "query": action_parameters,
            "include_code": include_code,
            "result": f"result found: {total_results}",
            "data": "No deliverable items found.",
            "total_nodes": total_results,
        }


class DefaultDeliveryAction(BaseDeliveryAction):
    """Default delivery action for tools that don't need special delivery handling."""

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Default fetch_next_code handler - just return None (no-op)."""
        return None


# Registry mapping tool names to delivery action classes
_DELIVERY_REGISTRY = {
    ToolName.SEMANTIC_SEARCH: SemanticSearchDeliveryAction,
    ToolName.DATABASE_SEARCH: DatabaseSearchDeliveryAction,
    # Other tools use default (no-op) delivery
    ToolName.SEARCH_KEYWORD: DefaultDeliveryAction,
    ToolName.APPLY_DIFF: DefaultDeliveryAction,
    ToolName.COMPLETION: DefaultDeliveryAction,
    ToolName.LIST_FILES: DefaultDeliveryAction,
    ToolName.TERMINAL_COMMANDS: DefaultDeliveryAction,
    ToolName.WEB_SCRAP: DefaultDeliveryAction,
    ToolName.WEB_SEARCH: DefaultDeliveryAction,
    ToolName.WRITE_TO_FILE: DefaultDeliveryAction,
}


def get_delivery_action(tool_enum: ToolName) -> BaseDeliveryAction:
    """
    Get delivery action handler for a tool.

    Args:
        tool_enum: The tool enum to get delivery handler for

    Returns:
        Delivery action instance for the tool
    """
    cls = _DELIVERY_REGISTRY.get(tool_enum, DefaultDeliveryAction)
    return cls()


def handle_fetch_next_request(action, tool_enum: ToolName) -> Optional[Dict[str, Any]]:
    """
    Centralized fetch_next_code handling for all tools.

    Args:
        action: AgentAction with parameters
        tool_enum: Tool enum to get appropriate delivery handler

    Returns:
        Response dict if this is a fetch_next request, None otherwise
    """
    if not action.parameters.get("fetch_next_code", False):
        return None

    delivery_action = get_delivery_action(tool_enum)
    return delivery_action.handle_fetch_next(action)


def register_delivery_queue_and_get_first_batch(
    action_type: str,
    action_parameters: Dict[str, Any],
    delivery_items: List[Dict[str, Any]],
    tool_enum: ToolName,
) -> Optional[Dict[str, Any]]:
    """
    Centralized delivery queue registration and first batch delivery.

    Args:
        action_type: String identifier for the action type
        action_parameters: Parameters for the action
        delivery_items: List of items to deliver
        tool_enum: Tool enum to get appropriate delivery handler

    Returns:
        First batch response or None if no items
    """
    if not delivery_items:
        return None

    delivery_action = get_delivery_action(tool_enum)
    return delivery_action.register_and_deliver_first_batch(
        action_type, action_parameters, delivery_items
    )


def register_delivery_queue_and_get_first_batch_with_line_limit(
    action_type: str,
    action_parameters: Dict[str, Any],
    delivery_items: List[Dict[str, Any]],
    tool_enum: ToolName,
    line_limit: int = 500,
) -> Optional[Dict[str, Any]]:
    """
    Centralized delivery queue registration and first batch delivery with line limit.

    This is specifically designed for database search to handle batching based on
    total line count rather than fixed node count.

    Args:
        action_type: String identifier for the action type
        action_parameters: Parameters for the action
        delivery_items: List of items to deliver
        tool_enum: Tool enum to get appropriate delivery handler
        line_limit: Maximum total lines allowed in batch

    Returns:
        First batch response or None if no items
    """
    if not delivery_items:
        return None

    delivery_action = get_delivery_action(tool_enum)

    # Use line-based delivery for database search
    if tool_enum == ToolName.DATABASE_SEARCH and hasattr(
        delivery_action, "register_and_deliver_first_batch_with_line_limit"
    ):
        return delivery_action.register_and_deliver_first_batch_with_line_limit(
            action_type, action_parameters, delivery_items, line_limit
        )
    else:
        # Fall back to regular delivery for other tools
        return delivery_action.register_and_deliver_first_batch(
            action_type, action_parameters, delivery_items
        )


def check_pending_delivery(
    action_type: str, action_parameters: Dict[str, Any], tool_enum: ToolName
) -> Optional[Dict[str, Any]]:
    """
    Check if there's a pending delivery for a query.

    Args:
        action_type: String identifier for the action type
        action_parameters: Parameters for the action
        tool_enum: Tool enum to get appropriate delivery handler

    Returns:
        Next pending item or None if no pending delivery
    """
    delivery_action = get_delivery_action(tool_enum)
    return delivery_action.check_pending_delivery(action_type, action_parameters)


__all__ = [
    "DELIVERY_QUEUE_CONFIG",
    "BaseDeliveryAction",
    "SemanticSearchDeliveryAction",
    "DatabaseSearchDeliveryAction",
    "DefaultDeliveryAction",
    "get_delivery_action",
    "handle_fetch_next_request",
    "register_delivery_queue_and_get_first_batch",
    "register_delivery_queue_and_get_first_batch_with_line_limit",
    "check_pending_delivery",
]
