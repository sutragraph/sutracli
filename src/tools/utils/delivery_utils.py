"""
Utility functions for delivery management shared between executors.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from services.agent.delivery_management import delivery_manager


def handle_fetch_next_request(
    action_type: str,
    action_parameters: Dict[str, Any],
    response_type: str = "query_complete"
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
        logger.debug("🔄 No query provided - using existing delivery queue for fetch_next_code")
        next_item = delivery_manager.get_next_item_from_existing_queue()
    else:
        # Check if this query matches the existing queue
        current_signature = delivery_manager._generate_query_signature(action_type, action_parameters)
        if delivery_manager._last_query_signature == current_signature:
            logger.debug("🔄 Same query provided - using existing delivery queue for fetch_next_code")
            next_item = delivery_manager.get_next_item_from_existing_queue()
        else:
            logger.debug("🔄 Different query provided with fetch_next_code - treating as new query")
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
    delivery_items: List[Dict[str, Any]]
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

    from .constants import DELIVERY_QUEUE_CONFIG

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
        from services.agent.agent_prompt.guidance_builder import (
            determine_semantic_batch_scenario,
            build_guidance_message,
            SearchType,
        )

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
    action_type: str,
    action_parameters: Dict[str, Any]
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
    include_code: bool = True
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
