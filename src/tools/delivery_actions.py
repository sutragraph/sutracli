"""
Tool Delivery Actions Factory

- Pattern: per-tool subclasses implement delivery batch functionality
- Usage: ActionExecutor asks factory for a delivery handler by tool name
- Centralizes all fetch_next_code and batch delivery logic
"""

from typing import Optional, Dict, Any, List
from loguru import logger
from services.agent.delivery_management import delivery_manager

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

    def register_and_deliver_first_item(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Register delivery queue and return first item."""
        return None

    def check_pending_delivery(
        self, action_type: str, action_parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if there's a pending delivery for this query."""
        return None

    def get_batch_size(self) -> int:
        """Get the batch size for this tool."""
        return 15  # Default batch size


class SemanticSearchDeliveryAction(BaseDeliveryAction):
    """Delivery actions for semantic search tool."""

    def get_batch_size(self) -> int:
        return DELIVERY_QUEUE_CONFIG.get("semantic_search", 15)

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_code requests for semantic search."""
        if not action.parameters.get("fetch_next_code", False):
            return None

        logger.debug("🔄 Fetch next batch request detected for semantic search")

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
            logger.debug(
                "🔄 Query provided with fetch_next_code - treating as new query"
            )
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

            return {
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
        remaining_count = len(delivery_items) - delivered_count

        # Combine data from all items
        combined_data = "\n\n".join(str(item.get("data", "")) for item in batch_items)

        return {
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


class DatabaseSearchDeliveryAction(BaseDeliveryAction):
    """Delivery actions for database search tool."""

    def get_batch_size(self) -> int:
        return DELIVERY_QUEUE_CONFIG.get("database_metadata_only", 30)

    def handle_fetch_next(self, action) -> Optional[Dict[str, Any]]:
        """Handle fetch_next_code requests for database search."""
        if not action.parameters.get("fetch_next_code", False):
            return None

        logger.debug("🔄 Fetch next batch request detected for database search")

        # Use existing delivery queue if no query provided, or same query
        query_provided = action.parameters.get("query")

        if not query_provided:
            logger.debug(
                "🔄 No query provided - using existing delivery queue for fetch_next_code"
            )
            next_item = delivery_manager.get_next_item_from_existing_queue()
        else:
            # Check if this query matches the existing queue
            current_signature = delivery_manager._generate_query_signature(
                "database", action.parameters
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

            return {
                "type": "tool_use",
                "tool_name": "database",
                "query_name": "fetch_next_code",
                "query": action.parameters,
                "data": next_item.get("data", ""),
                **base_response,
            }
        else:
            # No more items available
            base_response = {
                "total_nodes": 0,
                "result": "query_complete",
                "code_snippet": True,
            }

            return {
                "type": "tool_use",
                "tool_name": "database",
                "query_name": "fetch_next_code",
                "query": action.parameters,
                "data": "No more code chunks available. All items from the previous query have been delivered.",
                **base_response,
            }

    def register_and_deliver_first_item(
        self,
        action_type: str,
        action_parameters: Dict[str, Any],
        delivery_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Register delivery queue and return first item for database search."""
        if not delivery_items:
            return None

        delivery_manager.register_delivery_queue(
            action_type, action_parameters, delivery_items
        )
        return delivery_manager.get_next_item(action_type, action_parameters)

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

        batch_size = self.get_batch_size()
        batch_items = []

        for _ in range(batch_size):
            next_item = delivery_manager.get_next_item(action_type, action_parameters)
            if next_item:
                batch_items.append(next_item)
            else:
                break

        if not batch_items:
            return None

        # Format batch items into a single response (database search typically returns single items)
        # For now, return the first item since database search handles batching differently
        return batch_items[0]

    def check_pending_delivery(
        self, action_type: str, action_parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if there's a pending delivery for this query."""
        return delivery_manager.get_next_item(action_type, action_parameters)


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


def register_delivery_queue_and_get_first_item(
    action_type: str,
    action_parameters: Dict[str, Any],
    delivery_items: List[Dict[str, Any]],
    tool_enum: ToolName,
) -> Optional[Dict[str, Any]]:
    """
    Centralized delivery queue registration and first item delivery.

    Args:
        action_type: String identifier for the action type
        action_parameters: Parameters for the action
        delivery_items: List of items to deliver
        tool_enum: Tool enum to get appropriate delivery handler

    Returns:
        First item response or None if no items
    """
    if not delivery_items:
        return None

    delivery_action = get_delivery_action(tool_enum)
    return delivery_action.register_and_deliver_first_item(
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


def get_delivery_status(
    action_type: str, action_parameters: Dict[str, Any], tool_enum: ToolName
) -> Dict[str, Any]:
    """
    Get delivery status information for a query.

    Args:
        action_type: String identifier for the action type
        action_parameters: Parameters for the action
        tool_enum: Tool enum to get appropriate delivery handler

    Returns:
        Status information dict
    """
    return delivery_manager.get_queue_status(action_type, action_parameters)


def clear_delivery_queue(action_type: str, action_parameters: Dict[str, Any]) -> bool:
    """
    Clear a specific delivery queue.

    Args:
        action_type: String identifier for the action type
        action_parameters: Parameters for the action

    Returns:
        True if queue was cleared, False if queue didn't exist
    """
    return delivery_manager.clear_queue(action_type, action_parameters)


def clear_all_delivery_queues() -> int:
    """
    Clear all delivery queues.

    Returns:
        Number of queues that were cleared
    """
    return delivery_manager.clear_all_queues()


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


# Export configuration for external use
__all__ = [
    "DELIVERY_QUEUE_CONFIG",
    "BaseDeliveryAction",
    "SemanticSearchDeliveryAction",
    "DatabaseSearchDeliveryAction",
    "KeywordSearchDeliveryAction",
    "DefaultDeliveryAction",
    "get_delivery_action",
    "handle_fetch_next_request",
    "register_delivery_queue_and_get_first_batch",
    "register_delivery_queue_and_get_first_item",
    "check_pending_delivery",
    "get_delivery_status",
    "clear_delivery_queue",
    "clear_all_delivery_queues",
    "create_no_items_response",
]
