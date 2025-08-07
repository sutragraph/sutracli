"""
Available tools for the Roadmap Agent
"""

# Tool list for the roadmap agent (using string values directly to avoid import dependencies)
TOOL_LIST = [
    "tool_semantic_search",      # Find relevant code by similarity
    "tool_list_files",          # Explore project structure
    "tool_database_search",     # Query structured codebase data
    "tool_search_keyword",      # Search for patterns and symbols (ripgrep)
    "tool_terminal_commands",   # Execute commands for exploration
]
