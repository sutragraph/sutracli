"""
Constants for search executors including query mappings and configuration.
"""

# Chunking and search configuration
SEARCH_CONFIG = {
    "chunking_threshold": 700,  # Lines threshold for chunking (also determines "large" code)
    "chunk_size": 600,  # Max lines per chunk
}

# Semantic search specific configuration
SEMANTIC_SEARCH_CONFIG = {
    "total_nodes_limit": 30,  # Always fetch 30 nodes with code snippets
    "similarity_threshold": 0.0,
    "delivery_batch_size": 15,  # Serve 15 nodes at a time via delivery queue
    "block_chunk_threshold": 50,
    **SEARCH_CONFIG,
}

# Delivery queue configuration for different query types
DELIVERY_QUEUE_CONFIG = {
    "database_metadata_only": 30,  # Nodes per batch for all other database queries without code
    "semantic_search": 15,  # Nodes per batch for semantic search (always with code)
}

# Database query configuration mapping - ONLY 6 EXPOSED QUERIES FOR AGENT
DATABASE_QUERY_CONFIG = {
    "GET_FILE_BY_PATH": {
        "required_params": ["file_path"],
        "optional_params": ["start_line", "end_line"],
    },
    "GET_FILE_BLOCK_SUMMARY": {
        "required_params": ["file_path"],
        "optional_params": [],
    },
    "GET_BLOCK_DETAILS": {
        "required_params": ["block_id"],
        "optional_params": [],
    },
    "GET_DEPENDENCY_CHAIN": {
        "required_params": ["file_path"],
        "optional_params": ["depth"],
    },
}

# Error guidance messages for database queries
DATABASE_ERROR_GUIDANCE = {
    "GET_FILE_BY_PATH": "Try using semantic_search to find the correct file path first.",
    "GET_FILE_BLOCK_SUMMARY": "Ensure the file_path exists. Use semantic_search to find the correct file path first.",
    "GET_BLOCK_DETAILS": "Ensure the block_id exists. Use semantic_search to find block IDs first.",
    "GET_DEPENDENCY_CHAIN": "Ensure the file_path exists. Use semantic_search to find the correct file path first.",
}

# Guidance message templates
GUIDANCE_MESSAGES = {
    "fetch_next_chunk_NOTE": """\nNOTE: There are more results available. Use `"fetch_next_chunk" : true` to get next codes for your current query.""",
    "NO_RESULTS_FOUND": "No results found for {search_type} search. Try different search terms or methods. Verify parameters and query",
    "NODE_MISSING_CODE": "Node found but code content is not available.",
}
