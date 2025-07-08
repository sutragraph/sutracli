# TODO: Add directory-scoped semantic search support.

SEMANTIC_SEARCH_TOOL = """## semantic_search
Description: Find similar implementations and patterns in codebase. Use when you DON'T have specific function/class/file/method names (use database for specific names). Use for discovering existing patterns before creating new code.

Parameters:
- query: (required) The search terms to find similar implementations
- fetch_next_code: (optional) Set to true to fetch next chunks of results when more are available

Usage:
<semantic_search>
<query>search terms here</query>
<fetch_next_code>true|false</fetch_next_code>
</semantic_search>

Notes:
- When there are more results available, the user will give you data in chunks and will tell you to use fetch_next_code command - if the user does not tell you to use it, do not use it
- IMPORTANT: When using semantic search, always store relevant results in sutra memory if you are not making changes in current iteration or want this code for later use, as search results will not persist to next iteration

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

5. Fetch next chunk of results (only when user explicitly tells you to use fetch_next_code):
<semantic_search>
<query>database connection setup mongodb</query>
<fetch_next_code>true</fetch_next_code>
</semantic_search>
"""
