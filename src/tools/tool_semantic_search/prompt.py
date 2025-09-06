# TODO: Add directory-scoped semantic search support.

SEMANTIC_SEARCH_TOOL = """## semantic_search
Description: Find similar implementations and patterns in codebase using semantic similarity. Use when you DON'T have specific function/class/file/method names (use database for specific names). Use for discovering existing patterns before creating new code.

Parameters:
- query: (required) The search terms to find similar implementations - describe what you're looking for in natural language
- project_name: (optional) Name of the project to search within. If not provided, searches across all projects
- fetch_next_chunk: (optional) Set to true to fetch next chunks of results when more are available

Usage:
<semantic_search>
<query>search terms here</query>
<project_name>project_name_here</project_name>
<fetch_next_chunk>true|false</fetch_next_chunk>
</semantic_search>

Parameter Details:
- query: Use descriptive terms that capture the concept you're looking for (e.g., "user authentication", "file upload handler", "database connection setup")
- project_name: Specify a project name to limit search scope to that project only. Useful when you want to find patterns within a specific codebase
- fetch_next_chunk: Only use when the system explicitly tells you there are more results available - do not use preemptively

Notes:
- Results are delivered in batches for performance - the system will tell you if more chunks are available
- IMPORTANT: When using semantic search, always store relevant results in sutra memory if you are not making changes in current iteration or fetching more chunks or using new query or want this code for later use, as search results will not persist to next iteration
- The query parameter is passed through the XML structure and processed as action.parameters.get("query")

Examples:

1. Finding authentication patterns:
<semantic_search>
<query>user authentication login</query>
</semantic_search>

2. Finding API routing patterns:
<semantic_search>
<query>API routing router express</query>
</semantic_search>

3. Finding file upload implementations:
<semantic_search>
<query>file upload multipart</query>
</semantic_search>

4. Finding database connection patterns:
<semantic_search>
<query>database connection setup mongodb</query>
</semantic_search>

5. Finding patterns in a specific project:
<semantic_search>
<query>user authentication login</query>
<project_name>my_web_app</project_name>
</semantic_search>

6. Fetch next chunk of results (only when user explicitly tells you to use fetch_next_chunk):
<semantic_search>
<query>database connection setup mongodb</query>
<fetch_next_chunk>true</fetch_next_chunk>
</semantic_search>
"""
