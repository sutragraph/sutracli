DATABASE_SEARCH_TOOL = """## database
Description: Query structured codebase metadata and retrieve complete code content. Use this tool to get file information, code block summaries, and dependency chains. This tool provides structured access to the codebase knowledge graph.

Available Query Types:

1. GET_FILE_BLOCK_SUMMARY:
Gets summary of all code blocks (functions, classes, methods) within a file.
Required: query_name, file_path

2. GET_FILE_BY_PATH:
Gets complete file information by file path including content, language, and project details.
Required: query_name, file_path
Optional: start_line, end_line, fetch_next_chunk

3. GET_BLOCK_DETAILS:
Gets detailed information about a specific code block (function, class, method) including its content and all connections with other project nodes.
Required: query_name, block_id
Optional: fetch_next_chunk

Notes:
- Use complete file paths for all file operations
- When there are more results available, the user will give you data in chunks and will tell you to use fetch_next_chunk command - if the user does not tell you to use it, do not use it
- Most queries now use file_path directly - the system handles internal ID conversion automatically
- For block-specific operations, you may need block_id (obtained from GET_FILE_BLOCK_SUMMARY)
- Line numbers are 1-indexed
- Use this tool when you need structured codebase information and relationships
- IMPORTANT: When using database queries, always store relevant results in sutra memory if you are not making changes in current iteration or fetching more chunks or using new query or want this code for later use, as search results will not persist to next iteration

Usage:
<database>
<query_name>query_type</query_name>
<file_path>path/to/file</file_path>
<start_line>start_line_number</start_line>
<end_line>end_line_number</end_line>
<block_id>block_identifier</block_id>  <!-- Only for GET_BLOCK_DETAILS -->

<fetch_next_chunk>true|false</fetch_next_chunk>
</database>

Examples:

1. Get file information by path:
<database>
<query_name>GET_FILE_BY_PATH</query_name>
<file_path>/home/user/project/src/utils/helpers.py</file_path>
</database>

2. Get specific section of a file:
<database>
<query_name>GET_FILE_BY_PATH</query_name>
<file_path>/home/user/project/src/utils/helpers.py</file_path>
<start_line>20</start_line>
<end_line>50</end_line>
</database>

3. Get all code blocks in a file:
<database>
<query_name>GET_FILE_BLOCK_SUMMARY</query_name>
<file_path>/home/user/project/src/utils/helpers.py</file_path>
</database>

4. Get block details:
<database>
<query_name>GET_BLOCK_DETAILS</query_name>
<block_id>456</block_id>
</database>



6. Fetch next chunk of results (only when user explicitly tells you to use fetch_next_chunk):
<database>
<query_name>GET_FILE_BLOCK_SUMMARY</query_name>
<file_path>/home/user/project/src/utils/helpers.py</file_path>
<fetch_next_chunk>true</fetch_next_chunk>
</database>
"""
