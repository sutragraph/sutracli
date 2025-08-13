"""Sequential delivery manager for chunks and nodes."""

import uuid
from typing import Dict, Any, List, Optional, Iterator
from dataclasses import dataclass
from loguru import logger


@dataclass
class DeliveryItem:
    """Represents a single item to be delivered sequentially."""

    item_id: str
    item_type: str  # "database_node", "semantic_node", "chunk"
    data: Dict[str, Any]
    query_signature: str  # Unique signature for the query
    node_index: Optional[int] = None
    chunk_index: Optional[int] = None
    total_items: Optional[int] = None


class DeliveryManager:
    """Manages sequential delivery of chunks and nodes for repeated queries."""

    def __init__(self):
        # Store delivery queues by query signature
        self._delivery_queues: Dict[str, List[DeliveryItem]] = {}
        # Track current position in each queue
        self._queue_positions: Dict[str, int] = {}
        # Track completed deliveries
        self._completed_deliveries: Dict[str, bool] = {}
        # Track the last query signature to detect query changes
        self._last_query_signature: Optional[str] = None

    def _generate_query_signature(
        self, action_type: str, parameters: Dict[str, Any]
    ) -> str:
        """Generate a unique signature for a query to identify repeated calls."""
        # Create a consistent signature based on action type and key parameters
        key_params = {}

        if action_type == "database":
            # For database queries, use query_name and main parameters
            key_params = {
                "query_name": parameters.get("query_name"),
                "file_path": parameters.get("file_path"),
                "node_name": parameters.get("node_name"),
                "start_line": parameters.get("start_line"),
                "end_line": parameters.get("end_line"),
            }
        elif action_type == "semantic_search":
            # For semantic search, use only query (always returns code snippets now)
            key_params = {
                "query": parameters.get("query"),
            }

        # Remove None values and create sorted string
        filtered_params = {k: v for k, v in key_params.items() if v is not None}
        signature_parts = [action_type] + [
            f"{k}:{v}" for k, v in sorted(filtered_params.items())
        ]
        return "|".join(signature_parts)

    def register_delivery_queue(
        self, action_type: str, parameters: Dict[str, Any], items: List[Dict[str, Any]]
    ) -> str:
        """Register a new delivery queue for sequential processing."""
        logger.debug(f"📦 Registering delivery queue: {action_type} with {len(items)} items")

        query_signature = self._generate_query_signature(action_type, parameters)
        logger.debug(f"🔍 TRACE MANAGER: Generated signature: {query_signature}")

        # Check if this is a different query from the last one - if so, clear old data
        logger.debug(f"🔍 TRACE MANAGER: Last signature: {self._last_query_signature}")
        if self._last_query_signature and self._last_query_signature != query_signature:
            logger.debug(
                f"📦 Query changed from {self._last_query_signature} to {query_signature} - clearing old data"
            )
            self.clear_all_queues()

        # Update last query signature
        logger.debug(f"🔍 TRACE MANAGER: Setting last query signature to: {query_signature}")
        self._last_query_signature = query_signature

        # Convert items to DeliveryItem objects
        delivery_items = []

        for i, item in enumerate(items):
            chunk_info = item.get("chunk_info", {})


            delivery_item = DeliveryItem(
                item_id=str(uuid.uuid4()),
                item_type=f"{action_type}_item",
                data=item,
                query_signature=query_signature,
                node_index=item.get("node_index"),
                chunk_index=item.get("chunk_index"),
                total_items=len(items),
            )
            delivery_items.append(delivery_item)

        # BUGFIX: Prevent overwriting chunked delivery queues with fewer items
        # This prevents the bug where a 2-chunk queue gets overwritten with a 1-item queue
        if query_signature in self._delivery_queues:
            existing_queue_length = len(self._delivery_queues[query_signature])
            new_queue_length = len(delivery_items)

            # Check if existing queue has chunked content
            existing_has_chunks = any(
                item.data.get("chunk_info", {}).get("total_chunks", 1) > 1
                for item in self._delivery_queues[query_signature]
            )

            # Check if new queue has chunked content
            new_has_chunks = any(
                item.get("chunk_info", {}).get("total_chunks", 1) > 1
                for item in items
            )



            # Prevent overwriting chunked queue with fewer items or non-chunked content
            if existing_has_chunks and (new_queue_length < existing_queue_length or not new_has_chunks):
                logger.debug(f"📦 BUGFIX: Preventing queue overwrite - preserving existing chunked queue with {existing_queue_length} items")
                # Don't overwrite the queue, just update the last signature and return
                self._last_query_signature = query_signature
                current_pos = self._queue_positions[query_signature]
                is_complete = self._completed_deliveries[query_signature]
                logger.debug(f"📦 Preserved existing queue for {query_signature} - current position: {current_pos}, complete: {is_complete}")
                return query_signature

        # Store the queue (new queue or acceptable replacement)
        self._delivery_queues[query_signature] = delivery_items

        # Only reset position if this is a new queue or queue doesn't exist
        if query_signature not in self._queue_positions:
            self._queue_positions[query_signature] = 0
            self._completed_deliveries[query_signature] = False
            logger.debug(f"📦 NEW queue registered for {query_signature}")
        else:
            current_pos = self._queue_positions[query_signature]
            is_complete = self._completed_deliveries[query_signature]
            logger.debug(f"📦 EXISTING queue re-registered for {query_signature} - preserving position {current_pos}, complete: {is_complete}")
            # BUGFIX: Reset completion flag if we're re-registering the same queue
            # This can happen when line-based batching delivers partial content
            if is_complete and current_pos < len(delivery_items):
                logger.debug(f"📦 BUGFIX: Resetting completion flag - queue was marked complete but position {current_pos} < total items {len(delivery_items)}")
                self._completed_deliveries[query_signature] = False
        # If queue already exists, preserve the current position and completion status
        # This prevents position reset when re-registering the same chunked content

        final_position = self._queue_positions[query_signature]
        final_complete = self._completed_deliveries[query_signature]
        logger.debug(
            f"📦 Registered delivery queue for {query_signature} with {len(items)} items - current position: {final_position}, complete: {final_complete}"
        )

        return query_signature
    def get_next_item_from_existing_queue(self) -> Optional[Dict[str, Any]]:
        """Get the next item from the most recently used delivery queue without changing query signature."""
        if not self._last_query_signature:
            logger.debug("📦 No previous query signature found")
            return None

        query_signature = self._last_query_signature

        if query_signature not in self._delivery_queues:
            logger.debug(f"📦 No delivery queue found for {query_signature}")
            return None

        # Check if delivery is already complete
        is_complete = self._completed_deliveries.get(query_signature, False)
        if is_complete:
            current_pos = self._queue_positions.get(query_signature, 0)
            queue_length = len(self._delivery_queues.get(query_signature, []))
            logger.debug(f"📦 Delivery already complete for {query_signature} - position: {current_pos}, queue_length: {queue_length}")
            return None

        # Get current position and queue
        current_pos = self._queue_positions[query_signature]
        queue = self._delivery_queues[query_signature]

        # Check if we've reached the end
        if current_pos >= len(queue):
            self._completed_deliveries[query_signature] = True
            logger.debug(f"📦 Completed delivery queue for {query_signature}")
            return None

        # Get the next item
        next_item = queue[current_pos]

        # Advance position
        self._queue_positions[query_signature] = current_pos + 1
        logger.debug(f"📦 Advanced position from {current_pos} to {current_pos + 1}")

        # Add delivery metadata
        delivery_data = next_item.data.copy()
        delivery_data.update(
            {
                "delivery_info": {
                    "item_index": current_pos + 1,
                    "total_items": len(queue),
                    "query_signature": query_signature,
                    "is_last_item": current_pos + 1 == len(queue),
                }
            }
        )

        logger.debug(f"📦 Delivering item {current_pos + 1}/{len(queue)}")

        return delivery_data

    def get_next_item(
        self, action_type: str, parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get the next item for a given query, or None if queue is complete."""
        query_signature = self._generate_query_signature(action_type, parameters)

        # Check if this is a different query from the last one - if so, clear old data
        if self._last_query_signature and self._last_query_signature != query_signature:
            logger.debug(f"📦 Query changed - clearing old data")
            self.clear_all_queues()

        # Update last query signature
        self._last_query_signature = query_signature

        # Check if we have a queue for this signature
        if query_signature not in self._delivery_queues:
            logger.debug(f"📦 No delivery queue found for {query_signature}")
            return None

        # Check if delivery is already complete
        if self._completed_deliveries.get(query_signature, False):
            logger.debug(f"📦 Delivery already complete for {query_signature}")
            return None

        # Get current position and queue
        current_pos = self._queue_positions[query_signature]
        queue = self._delivery_queues[query_signature]

        # Check if we've reached the end
        if current_pos >= len(queue):
            self._completed_deliveries[query_signature] = True
            logger.debug(f"📦 SETTING COMPLETION FLAG: Completed delivery queue for {query_signature} (pos {current_pos} >= length {len(queue)})")
            return None

        # Get the next item
        next_item = queue[current_pos]

        # Advance position
        self._queue_positions[query_signature] = current_pos + 1

        # Add delivery metadata
        delivery_data = next_item.data.copy()
        delivery_data.update(
            {
                "delivery_info": {
                    "item_index": current_pos + 1,
                    "total_items": len(queue),
                    "query_signature": query_signature,
                    "is_last_item": (current_pos + 1) >= len(queue),
                }
            }
        )

        logger.debug(
            f"📦 Delivering item {current_pos + 1}/{len(queue)} for {query_signature}"
        )
        return delivery_data

    def has_pending_items(self, action_type: str, parameters: Dict[str, Any]) -> bool:
        """Check if there are pending items for a given query."""
        query_signature = self._generate_query_signature(action_type, parameters)

        if query_signature not in self._delivery_queues:
            return False

        if self._completed_deliveries.get(query_signature, False):
            return False

        current_pos = self._queue_positions[query_signature]
        queue_length = len(self._delivery_queues[query_signature])

        return current_pos < queue_length

    def get_queue_status(
        self, action_type: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get status information about a delivery queue."""
        query_signature = self._generate_query_signature(action_type, parameters)

        if query_signature not in self._delivery_queues:
            return {"exists": False}

        current_pos = self._queue_positions[query_signature]
        total_items = len(self._delivery_queues[query_signature])
        is_complete = self._completed_deliveries.get(query_signature, False)

        return {
            "exists": True,
            "query_signature": query_signature,
            "current_position": current_pos,
            "total_items": total_items,
            "remaining_items": max(0, total_items - current_pos),
            "is_complete": is_complete,
            "progress_percentage": (
                (current_pos / total_items * 100) if total_items > 0 else 0
            ),
        }

    def clear_queue(self, action_type: str, parameters: Dict[str, Any]) -> bool:
        """Clear a specific delivery queue."""
        query_signature = self._generate_query_signature(action_type, parameters)

        if query_signature in self._delivery_queues:
            del self._delivery_queues[query_signature]
            del self._queue_positions[query_signature]
            del self._completed_deliveries[query_signature]
            logger.debug(f"📦 Cleared delivery queue for {query_signature}")
            return True
        return False

    def clear_all_queues(self) -> int:
        """Clear all delivery queues and return the number cleared."""
        count = len(self._delivery_queues)
        self._delivery_queues.clear()
        self._queue_positions.clear()
        self._completed_deliveries.clear()
        self._last_query_signature = None
        logger.debug(f"📦 Cleared all {count} delivery queues")
        return count

    def get_next_item_info(
        self, action_type: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get information about the next item without consuming it."""
        query_signature = self._generate_query_signature(action_type, parameters)

        if query_signature not in self._delivery_queues:
            return {
                "has_next": False,
                "total_items": 0,
                "current_position": 0,
                "remaining_items": 0,
            }

        current_pos = self._queue_positions[query_signature]
        total_items = len(self._delivery_queues[query_signature])
        remaining_items = max(0, total_items - current_pos)

        return {
            "has_next": remaining_items > 0,
            "total_items": total_items,
            "current_position": current_pos,
            "remaining_items": remaining_items,
            "is_complete": self._completed_deliveries.get(query_signature, False),
        }


# Global instance for the application
delivery_manager = DeliveryManager()
