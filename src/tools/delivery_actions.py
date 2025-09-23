"""
Tool Delivery Actions Factory

- Pattern: per-tool subclasses implement delivery batch functionality
- Centralizes all fetch_next_chunk and batch delivery logic
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from services.agent.delivery_management import delivery_manager

# Delivery queue configuration for different tool types
DELIVERY_QUEUE_CONFIG = {
    "database_metadata_only": 30,  # Nodes per batch for all other database queries without code
    "semantic_search": 15,  # Nodes per batch for semantic search (always with code)
}


class BaseDeliveryAction:
    """Base class for tool-specific delivery actions."""

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_chunk requests for this tool."""
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

    def register_and_deliver_first_batch_with_line_limit(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
        line_limit: int = 500,
    ) -> Optional[Dict[str, Any]]:
        """Register delivery queue and return first batch with line limit."""
        # Default implementation falls back to regular delivery
        return self.register_and_deliver_first_batch(
            action_type, action_parameters, delivery_items
        )

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
        """Handle fetch_next_chunk requests for semantic search."""
        fetch_next_chunk = action.parameters.get("fetch_next_chunk")
        # Only handle as fetch_next if explicitly set to True
        if fetch_next_chunk is not True:
            return None

        logger.debug("🔄 Fetch next request for semantic search")

        batch_size = self.get_batch_size()
        batch_items = []

        # Only use existing delivery queue if NO query is provided (just fetch_next_chunk)
        # If query is provided along with fetch_next_chunk, treat it as a new query
        if not action.parameters.get("query"):
            logger.debug(
                "🔄 No query provided - using existing delivery queue for fetch_next_chunk"
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

            # Add project header if project_name is available in any of the batch items
            project_name = None
            for item in batch_items:
                if item.get("project_name"):
                    project_name = item.get("project_name")
                    break

            if project_name:
                final_data = f"PROJECT: {project_name}\n{final_data}"

            event = {
                "tool_name": "semantic_search",
                "type": "tool_use",
                "query": batch_items[0].get("query", "fetch_next_chunk"),
                "result": f"Found {total_nodes} nodes",
                "data": final_data,
                "code_snippet": True,
                "total_nodes": total_nodes,
                "project_name": project_name,
                "batch_info": {
                    "delivered_count": delivered_count,
                    "remaining_count": remaining_count,
                    "batch_size": batch_size,
                },
            }

            return event
        else:
            # No more items available
            return {
                "tool_name": "semantic_search",
                "type": "tool_use",
                "query": action.parameters.get("query", "fetch_next_chunk"),
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
        remaining_count = total_nodes - delivered_count

        # Combine data from all items
        combined_data = "\n\n".join(str(item.get("data", "")) for item in batch_items)

        # Add project header if project_name is available in any of the batch items
        project_name = None
        for item in batch_items:
            if item.get("project_name"):
                project_name = item.get("project_name")
                break

        if project_name:
            combined_data = f"PROJECT: {project_name}\n{combined_data}"

        event = {
            "type": "tool_use",
            "tool_name": "semantic_search",
            "query": query,
            "result": f"result found: {total_nodes}",
            "data": combined_data,
            "code_snippet": True,
            "total_nodes": total_nodes,
            "project_name": project_name,
            "batch_info": {
                "delivered_count": delivered_count,
                "remaining_count": remaining_count,
                "batch_size": batch_size,
            },
        }

        return event

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
        batch_nodes = []
        total_lines = 0

        for i, node in enumerate(delivery_items):
            code_content = node.get("code_snippet", "") or node.get("data", "")

            if code_content:
                node_lines = len(str(code_content).split("\n"))

                # Check if adding this node would exceed the limit
                if total_lines + node_lines > line_limit and batch_nodes:
                    # Don't add this node, return current batch
                    break

                batch_nodes.append(node)
                total_lines += node_lines
            else:
                # Add nodes without code content
                batch_nodes.append(node)

        return batch_nodes

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

        # Check if this is chunked content
        is_chunked_content = any(
            item.get("chunk_info")
            and item.get("chunk_info", {}).get("total_chunks", 1) > 1
            for item in delivery_items
        )

        if is_chunked_content:
            logger.debug("📦 Detected chunked content - delivering first chunk")
            # Sort chunks by chunk_num to ensure correct order and get the first chunk
            sorted_chunks = sorted(
                delivery_items,
                key=lambda x: x.get("chunk_info", {}).get("chunk_num", 1),
            )
            first_chunk = sorted_chunks[0]

            # Advance delivery manager position by 1 to mark first chunk as delivered
            query_signature = delivery_manager._generate_query_signature(
                action_type, action_parameters
            )
            if query_signature in delivery_manager._queue_positions:
                delivery_manager._queue_positions[query_signature] = 1
                logger.debug("📦 Advanced queue position to 1 for first chunk delivery")

            chunk_info = first_chunk.get("chunk_info", {})
            chunk_num = chunk_info.get("chunk_num", 1)
            total_chunks = chunk_info.get("total_chunks", 1)
            original_file_lines = chunk_info.get("original_file_lines", 0)
            start_line = chunk_info.get("start_line", 1)
            end_line = chunk_info.get("end_line", 0)

            logger.debug(
                f"📦 Delivering chunk {chunk_num}/{total_chunks} (lines {start_line}-{end_line})"
            )

            # Build the event for the first chunk
            query_name = action_parameters.get("query_name", "unknown")
            is_metadata_only = query_name == "GET_FILE_BLOCK_SUMMARY"

            event = {
                "type": "tool_use",
                "tool_name": "database",
                "query_name": query_name,
                "query": action_parameters,
                "result": "found: 1",
                "data": first_chunk.get("data", ""),
                "code_snippet": not is_metadata_only,
                "total_nodes": 1,
                "batch_info": {
                    "delivered_count": 1,
                    "remaining_count": 0 if total_chunks == 1 else 1,
                    "delivered_lines": end_line - start_line + 1,
                    "total_lines": original_file_lines,
                },
                "chunk_info": chunk_info,
            }

            return event
        else:
            # For non-chunked content, use line-based batching
            line_based_batch = self.get_line_based_batch(delivery_items, line_limit)

            if not line_based_batch:
                return None

            # Advance delivery queue position
            query_signature = delivery_manager._generate_query_signature(
                action_type, action_parameters
            )
            delivered_count = len(line_based_batch)

            if query_signature in delivery_manager._queue_positions:
                delivery_manager._queue_positions[query_signature] = delivered_count
                logger.debug(f"📦 Advanced queue position to {delivered_count}")

            # Build event for non-chunked content
            combined_data = "\n\n".join(
                str(item.get("data", "")) for item in line_based_batch
            )

            query_name = action_parameters.get("query_name", "unknown")
            is_metadata_only = query_name == "GET_FILE_BLOCK_SUMMARY"

            total_nodes = len(delivery_items)
            remaining_nodes = total_nodes - delivered_count

            event = {
                "type": "tool_use",
                "tool_name": "database",
                "query_name": query_name,
                "query": action_parameters,
                "result": "found: {}".format(total_nodes),
                "data": combined_data,
                "code_snippet": not is_metadata_only,
                "total_nodes": total_nodes,
                "batch_info": {
                    "delivered_count": delivered_count,
                    "remaining_count": remaining_nodes,
                    "delivered_lines": len(combined_data.split("\n")),
                    "total_lines": sum(
                        len(str(item.get("data", "")).split("\n"))
                        for item in delivery_items
                    ),
                },
            }

            return event

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_chunk requests for database search."""
        fetch_next_chunk = action.parameters.get("fetch_next_chunk")
        # Only handle as fetch_next if explicitly set to True
        if fetch_next_chunk is not True:
            return None
        logger.debug("🔄 Fetch next request for database search")

        # Use existing delivery queue if no query provided, or same query
        query_provided = action.parameters.get("query")

        if not query_provided:
            logger.debug("🔄 Using existing delivery queue for fetch_next_chunk")
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
                "query_name": "fetch_next_chunk",
                "query": action.parameters,
                "data": next_item.get("data", ""),
                **base_response,
            }

            return event
        else:
            logger.debug("🔍 TRACE FETCH: ❌ *** NO NEXT ITEM AVAILABLE ***")

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

            logger.debug("🔍 TRACE FETCH: *** RETURNING QUERY_COMPLETE ***")
            return {
                "type": "tool_use",
                "tool_name": "database",
                "query_name": "fetch_next_chunk",
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

        # Check if this is chunked content - if so, delegate to line limit method
        is_chunked_content = any(
            item.get("chunk_info")
            and item.get("chunk_info", {}).get("total_chunks", 1) > 1
            for item in delivery_items
        )

        if is_chunked_content:
            logger.debug("📦 Chunked content detected - using line limit method")
            return self.register_and_deliver_first_batch_with_line_limit(
                action_type, action_parameters, delivery_items, 500
            )

        # For non-chunked content, proceed with normal delivery
        delivery_manager.register_delivery_queue(
            action_type, action_parameters, delivery_items
        )

        logger.debug(f"📦 Registered {len(delivery_items)} items for {action_type}")

        # Get the first item from the delivery manager to advance the queue
        next_item = delivery_manager.get_next_item(action_type, action_parameters)
        if not next_item:
            return None

        # Add project header if project information is available
        project_name = next_item.get("project_name")
        if project_name:
            data = next_item.get("data", "")
            if data:
                next_item["data"] = f"PROJECT: {project_name}\n{data}"

        return next_item

    def check_pending_delivery(
        self, action_type: str, action_parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if there's a pending delivery for this query."""
        # If this is a fetch_next_chunk request, handle it as such
        fetch_next_chunk = action_parameters.get("fetch_next_chunk")
        if fetch_next_chunk is True:
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


class ListFilesDeliveryAction(BaseDeliveryAction):
    """Delivery action for list_files tool."""

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_chunk requests for list_files."""
        fetch_next_chunk = action.parameters.get("fetch_next_chunk")
        # Only handle as fetch_next if explicitly set to True
        if fetch_next_chunk is not True:
            return None

        logger.debug("🔄 Fetch next request for list_files")

        next_item = delivery_manager.get_next_item_from_existing_queue()

        if next_item:
            return next_item
        else:
            # No more items available
            return {
                "type": "tool_use",
                "tool_name": "list_files",
                "query": action.parameters,
                "result": "query_complete",
                "data": "No more chunks available. All content has been delivered.",
                "code_snippet": True,
                "total_nodes": 0,
            }

    def register_and_deliver_first_batch(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Handle delivery queue registration for list_files."""
        if not delivery_items:
            return None

        # If only one item and no chunk_info, return as-is (no chunking needed)
        if len(delivery_items) == 1 and "chunk_info" not in delivery_items[0]:
            return delivery_items[0]

        # Register all items with delivery manager for chunked content
        delivery_manager.register_delivery_queue(
            action_type, action_parameters, delivery_items
        )

        # Get first item
        first_item = delivery_manager.get_next_item(action_type, action_parameters)
        if not first_item:
            return delivery_items[0]

        # Add batch info if this is chunked content
        if first_item.get("chunk_info"):
            chunk_info = first_item["chunk_info"]
            total_chunks = chunk_info.get("total_chunks", 1)

            first_item["batch_info"] = {
                "delivered_count": 1,
                "remaining_count": 0 if total_chunks == 1 else 1,
                "batch_size": 1,
            }

        return first_item


class SearchKeywordDeliveryAction(BaseDeliveryAction):
    """Delivery action for search_keyword tool."""

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_chunk requests for search_keyword."""
        fetch_next_chunk = action.parameters.get("fetch_next_chunk")
        # Only handle as fetch_next if explicitly set to True
        if fetch_next_chunk is not True:
            return None

        logger.debug("🔄 Fetch next request for search_keyword")

        next_item = delivery_manager.get_next_item_from_existing_queue()

        if next_item:
            return next_item
        else:
            # No more items available
            return {
                "type": "tool_use",
                "tool_name": "search_keyword",
                "query": action.parameters,
                "result": "query_complete",
                "data": "No more chunks available. All content has been delivered.",
                "code_snippet": True,
                "total_nodes": 0,
            }

    def register_and_deliver_first_batch(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Handle delivery queue registration for search_keyword."""
        if not delivery_items:
            return None

        # If only one item and no chunk_info, return as-is (no chunking needed)
        if len(delivery_items) == 1 and "chunk_info" not in delivery_items[0]:
            return delivery_items[0]

        # Register all items with delivery manager for chunked content
        delivery_manager.register_delivery_queue(
            action_type, action_parameters, delivery_items
        )

        # Get first item
        first_item = delivery_manager.get_next_item(action_type, action_parameters)
        if not first_item:
            return delivery_items[0]

        # Add batch info if this is chunked content
        if first_item.get("chunk_info"):
            chunk_info = first_item["chunk_info"]
            total_chunks = chunk_info.get("total_chunks", 1)

            first_item["batch_info"] = {
                "delivered_count": 1,
                "remaining_count": 0 if total_chunks == 1 else 1,
                "batch_size": 1,
            }

        return first_item


class DefaultDeliveryAction(BaseDeliveryAction):
    """Default delivery action for tools that don't need special delivery handling."""

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Default fetch_next_chunk handler - just return None (no-op)."""
        return None

    def register_and_deliver_first_batch(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Handle delivery for default tools that return single results."""
        if not delivery_items:
            return None

        # For default tools, just return the first item as-is
        # These tools typically don't need batching or special processing
        return delivery_items[0]


# Registry mapping tool names to delivery action classes
_DELIVERY_REGISTRY = {
    "semantic_search": SemanticSearchDeliveryAction,
    "database": DatabaseSearchDeliveryAction,
    "search_keyword": SearchKeywordDeliveryAction,
    "list_files": ListFilesDeliveryAction,
    # Other tools use default (no-op) delivery
    "apply_diff": DefaultDeliveryAction,
    "completion": DefaultDeliveryAction,
    "terminal_commands": DefaultDeliveryAction,
    "web_scrap": DefaultDeliveryAction,
    "web_search": DefaultDeliveryAction,
    "write_to_file": DefaultDeliveryAction,
}


def get_delivery_action(tool_name: str) -> BaseDeliveryAction:
    """
    Get delivery action handler for a tool.

    Args:
        tool_name: The tool name to get delivery handler for

    Returns:
        Delivery action instance for the tool
    """
    cls = _DELIVERY_REGISTRY.get(tool_name, DefaultDeliveryAction)
    return cls()


def handle_fetch_next_request(action, tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Centralized fetch_next_chunk handling for all tools.

    Args:
        action: AgentAction with parameters
        tool_name: Tool name to get appropriate delivery handler

    Returns:
        Response dict if this is a fetch_next request, None otherwise
    """
    fetch_next_chunk = action.parameters.get("fetch_next_chunk")
    # Only handle as fetch_next if explicitly set to True
    if fetch_next_chunk is not True:
        return None

    delivery_action = get_delivery_action(tool_name)
    return delivery_action.handle_fetch_next(action)


def register_delivery_queue_and_get_first_batch(
    action_type: str,
    action_parameters: Dict[str, Any],
    delivery_items: List[Dict[str, Any]],
    tool_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Centralized delivery queue registration and first batch delivery.

    Args:
        action_type: String identifier for the action type
        action_parameters: Parameters for the action
        delivery_items: List of items to deliver
        tool_name: Tool name to get appropriate delivery handler

    Returns:
        First batch response or None if no items
    """
    if not delivery_items:
        return None

    delivery_action = get_delivery_action(tool_name)
    return delivery_action.register_and_deliver_first_batch(
        action_type, action_parameters, delivery_items
    )


def register_delivery_queue_and_get_first_batch_with_line_limit(
    action_type: str,
    action_parameters: Dict[str, Any],
    delivery_items: List[Dict[str, Any]],
    tool_name: str,
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
        tool_name: str,
        line_limit: int = 500

    Returns:
        First batch response or None if no items
    """
    if not delivery_items:
        return None

    delivery_action = get_delivery_action(tool_name)

    # Use line-based delivery for database search
    if tool_name == "database" and hasattr(
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
    action_type: str, action_parameters: Dict[str, Any], tool_name: str
) -> Optional[Dict[str, Any]]:
    """
    Check if there's a pending delivery for a query.

    Args:
        action_type: String identifier for the action type
        action_parameters: Parameters for the action
        tool_name: Tool enum to get appropriate delivery handler

    Returns:
        Next pending item or None if no pending delivery
    """
    delivery_action = get_delivery_action(tool_name)
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
