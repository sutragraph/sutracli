"""
Database utility functions for agent action executors.
"""

from src.graph.sqlite_client import SQLiteConnection
from loguru import logger


def get_node_details(node_id: int, project_id: int = None, db_connection=None):
    """
    Get detailed information about a specific node from the database.
    
    Args:
        node_id: The ID of the node to retrieve
        project_id: Optional project ID for filtering
        db_connection: Optional database connection to use
        
    Returns:
        Dictionary with node details or None if not found
    """
    try:
        db_connection = db_connection or SQLiteConnection()
        cursor = db_connection.connection.cursor()
        from src.queries.agent_queries import GET_NODE_DETAILS
        cursor.execute(
            GET_NODE_DETAILS, {"node_id": node_id, "project_id": project_id}
        )
        row = cursor.fetchone()
        if row:
            return {
                "node_id": row[0],
                "type": row[1],
                "name": row[2],
                "lines": row[3],
                "code_snippet": row[4] or "",
                "properties": row[5],
                "file_path": row[6] or "",
                "language": row[7],
                "project_name": row[9],
                "project_id": row[10],
            }
    except Exception as e:
        logger.error(f"Error getting node details: {e}")
    return None
