DATABASE_SEARCH_TOOL = """## database
Description: Query structured codebase metadata and retrieve complete code content. Use this tool to get file information, code block summaries, and dependency chains. This tool provides structured access to the codebase knowledge graph.

Available Query Types:

1. GET_FILE_BY_PATH:
Gets complete file information by file path including content, language, and project details.
Required: query_name, file_path
Optional: code_content, fetch_next_code

2. GET_FILE_BLOCK_SUMMARY:
Gets summary of all code blocks (functions, classes, methods) within a file.
Required: query_name, file_path
Optional: code_content, fetch_next_code

3. GET_BLOCK_DETAILS:
====TODO====

4. GET_FILE_IMPORTS:
Gets all imports/dependencies for a specific file.
Required: query_name, file_path
Optional: code_content, fetch_next_code

5. GET_DEPENDENCY_CHAIN:
Gets multi-hop dependency chain for a file showing recursive dependencies.
Required: query_name, file_path
Optional: depth, code_content, fetch_next_code

Notes:
- All file paths should be relative to the current workspace directory ({current_dir})
- When code_content is true, the response includes the complete actual source code implementation
- When there are more results available, the user will give you data in chunks and will tell you to use fetch_next_code command - if the user does not tell you to use it, do not use it
- Most queries now use file_path directly - the system handles internal ID conversion automatically
- For block-specific operations, you may need block_id (obtained from GET_FILE_BLOCK_SUMMARY)
- Line numbers are 1-indexed
- Use this tool when you need structured codebase information and relationships
- IMPORTANT: When using database queries, always store relevant results in sutra memory if you are not making changes in current iteration or want this code for later use, as search results will not persist to next iteration

Usage:
<database>
<query_name>query_type</query_name>
<file_path>path/to/file</file_path>
<block_id>block_identifier</block_id>  <!-- Only for GET_BLOCK_DETAILS -->
<depth>dependency_depth</depth>  <!-- Only for GET_DEPENDENCY_CHAIN -->
<code_content>true|false</code_content>
<fetch_next_code>true|false</fetch_next_code>
</database>

Examples:

1. Get file information by path:
<database>
<query_name>GET_FILE_BY_PATH</query_name>
<file_path>src/utils/helpers.py</file_path>
<code_content>true</code_content>
</database>

2. Get all code blocks in a file:
<database>
<query_name>GET_FILE_BLOCK_SUMMARY</query_name>
<file_path>src/utils/helpers.py</file_path>
<code_content>true</code_content>
</database>

3. Get block details:
<database>
<query_name>GET_BLOCK_DETAILS</query_name>
<block_id>456</block_id>
====TODO====
</database>

4. Get file imports and dependencies:
<database>
<query_name>GET_FILE_IMPORTS</query_name>
<file_path>src/utils/helpers.py</file_path>
<code_content>true</code_content>
</database>

5. Get dependency chain for a file:
<database>
<query_name>GET_DEPENDENCY_CHAIN</query_name>
<file_path>src/utils/helpers.py</file_path>
<depth>3</depth>
<code_content>true</code_content>
</database>

6. Fetch next chunk of results (only when user explicitly tells you to use fetch_next_code):
<database>
<query_name>GET_FILE_BLOCK_SUMMARY</query_name>
<file_path>src/utils/helpers.py</file_path>
<code_content>true</code_content>
<fetch_next_code>true</fetch_next_code>
</database>
"""
