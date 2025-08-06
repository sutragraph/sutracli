"""
Node details utility functions for bridging semantic search results to database records.
"""

import re
from typing import Dict, Any, Optional
from loguru import logger
from graph.sqlite_client import SQLiteConnection
from queries.agent_queries import GET_CODE_BLOCK_BY_ID, GET_FILE_BY_ID


def get_node_details(node_id: str) -> Optional[Dict[str, Any]]:
    """
    Bridge function to convert semantic search node_id to actual database record.
    
    This function parses node IDs like "block_123" or "file_456" and routes to 
    the appropriate database query to get the full details.
    
    Args:
        node_id: Node ID from semantic search (e.g., "block_123", "file_456")
        
    Returns:
        Dictionary with node details or None if not found
        
    Example:
        node_details = get_node_details("block_123")
        # Returns: {
        #   "id": 123, "type": "function", "name": "uploadAvatar",
        #   "content": "def uploadAvatar(user_id, file):\n    ...",
        #   "start_line": 45, "end_line": 67, "file_path": "src/services/user_service.py",
        #   "project_name": "backend_api", ...
        # }
    """
    if not node_id:
        return None
        
    try:
        db_connection = SQLiteConnection()
        
        # Parse node_id format
        if node_id.startswith("block_"):
            # Extract block ID and query code_blocks table
            block_id_match = re.match(r"block_(\d+)", node_id)
            if not block_id_match:
                logger.warning(f"Invalid block node_id format: {node_id}")
                return None
                
            block_id = int(block_id_match.group(1))
            results = db_connection.execute_query(GET_CODE_BLOCK_BY_ID, (block_id,))
            
            if results:
                result = results[0]
                # Convert to dictionary format expected by tools
                return {
                    "id": result["id"],
                    "type": result["type"],
                    "name": result["name"],
                    "content": result["content"],
                    "code_snippet": result["content"],  # Alias for compatibility
                    "start_line": result["start_line"],
                    "end_line": result["end_line"],
                    "lines": [result["start_line"], result["end_line"]],  # Format expected by tools
                    "file_path": result["file_path"],
                    "file_id": result["file_id"],
                    "language": result["language"],
                    "project_name": result["project_name"],
                    "project_id": result["project_id"],
                    "parent_block_id": result.get("parent_block_id"),
                    "node_type": result["type"],  # Alias for compatibility
                }
                
        elif node_id.startswith("file_"):
            # Extract file ID and query files table
            file_id_match = re.match(r"file_(\d+)", node_id)
            if not file_id_match:
                logger.warning(f"Invalid file node_id format: {node_id}")
                return None
                
            file_id = int(file_id_match.group(1))
            results = db_connection.execute_query(GET_FILE_BY_ID, (file_id,))
            
            if results:
                result = results[0]
                # Convert to dictionary format expected by tools
                return {
                    "id": result["id"],
                    "type": "file",
                    "name": result["file_path"].split("/")[-1],  # Extract filename
                    "content": result["content"],
                    "code_snippet": result["content"],  # Alias for compatibility
                    "file_path": result["file_path"],
                    "language": result["language"],
                    "project_name": result["project_name"],
                    "project_id": result["project_id"],
                    "content_hash": result["content_hash"],
                    "block_count": result["block_count"],
                    "node_type": "file",  # Alias for compatibility
                    # For files, we don't have specific line ranges
                    "lines": None,
                    "start_line": None,
                    "end_line": None,
                }
        else:
            logger.warning(f"Unknown node_id format: {node_id}")
            return None
            
        logger.warning(f"Node not found for ID: {node_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting node details for {node_id}: {e}")
        return None
