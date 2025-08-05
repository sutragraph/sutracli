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
    "similarity_threshold": 0.2,
    "delivery_batch_size": 15,  # Serve 15 nodes at a time via delivery queue
    **SEARCH_CONFIG,
}

# Delivery queue configuration for different query types
DELIVERY_QUEUE_CONFIG = {
    "keyword_search_with_code": 10,  # Nodes per batch for keyword search with code
    "keyword_search_metadata": 30,  # Nodes per batch for keyword search metadata only
    "database_metadata_only": 30,  # Nodes per batch for all other database queries without code
    "semantic_search": 15,  # Nodes per batch for semantic search (always with code)
}

# Database query configuration mapping
DATABASE_QUERY_CONFIG = {
    "GET_NODES_BY_EXACT_NAME": {
        "required_params": ["name"],
        "optional_params": [],
    },
    "GET_NODES_BY_KEYWORD_SEARCH": {
        "required_params": ["keyword"],
        "optional_params": [],
    },
    "GET_CODE_FROM_FILE": {
        "required_params": ["file_path"],
        "optional_params": [],
    },
    "GET_CODE_FROM_FILE_LINES": {
        "required_params": ["file_path"],
        "optional_params": ["start_line", "end_line"],
    },
    "GET_ALL_NODE_NAMES_FROM_FILE": {
        "required_params": ["file_path"],
        "optional_params": [],
    },
    "GET_FUNCTION_CALLERS": {
        "required_params": ["function_name"],
        "optional_params": [],
    },
    "GET_FUNCTION_CALLEES": {
        "required_params": ["function_name"],
        "optional_params": [],
    },
    "GET_FILE_DEPENDENCIES": {
        "required_params": ["file_path"],
        "optional_params": [],
    },
}

# Error guidance messages for database queries
DATABASE_ERROR_GUIDANCE = {
    "GET_CODE_FROM_FILE": "Try using semantic_search to find the path/to/file first.",
    "GET_NODES_BY_EXACT_NAME": "Try using semantic_search for partial or fuzzy matching.",
    "GET_NODES_BY_KEYWORD_SEARCH": "Try different keywords, broader search terms, or use semantic_search for conceptual matching.",
    "GET_FUNCTION_CALLERS": "Ensure the function exists and has callers in the codebase. Use different search terms if no callers found.",
    "GET_FUNCTION_CALLEES": "Ensure the function exists and calls other functions. Use different search terms if no callees found.",
}

# Guidance message templates
GUIDANCE_MESSAGES = {
    "FETCH_NEXT_CODE_NOTE": "\nNOTE: There are more results available. Use <fetch_next_code>true</fetch_next_code> to get next codes for your current query.",
    "NO_RESULTS_FOUND": "No results found for {search_type} search. Try different search terms or methods.",
    "NODE_MISSING_CODE": "Node found but code content is not available.",
}
