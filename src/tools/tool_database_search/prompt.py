DATABASE_SEARCH_TOOL = """## database
Description: Query structured codebase metadata and retrieve complete code content. Use this tool to get full function code, complete file content, class definitions, and detailed code structures. This tool retrieves the actual source code when you know exact identifiers like function names, class names, or file paths. Perfect for getting complete implementations.

Available Query Types:

1. GET_NODES_BY_EXACT_NAME:
Searches for nodes by exact name and retrieves their complete code implementation (functions, classes, files, methods).
Required: query_name, name
Optional: code_content, fetch_next_code

2. GET_CODE_FROM_FILE:
Retrieves complete file content with all code, functions, classes, and implementations.
Required: query_name, file_path
Optional: code_content, fetch_next_code

3. GET_CODE_FROM_FILE_LINES:
Retrieves specific lines from a file with the actual code content.
Required: query_name, file_path, start_line, end_line

4. GET_ALL_NODE_NAMES_FROM_FILE:
Gets all node names from a specific file and optionally their complete code implementations.
Required: query_name, file_path
Optional: code_content, fetch_next_code

5. GET_FUNCTION_CALLERS:
Finds all functions that call a specific function and retrieves their complete code.
Required: query_name, function_name
Optional: code_content, fetch_next_code

6. GET_FUNCTION_CALLEES:
Finds all functions called by a specific function and retrieves their complete code.
Required: query_name, function_name
Optional: code_content, fetch_next_code

7. GET_FILE_DEPENDENCIES:
Gets file dependencies for a specific file and optionally retrieves the complete code of dependent files.
Required: query_name, file_path
Optional: code_content, fetch_next_code

Notes:
- All file paths should be relative to the current workspace directory ({current_dir})
- When code_content is true, the response includes the complete actual source code implementation
- When there are more results available, the user will give you data in chunks and will tell you to use fetch_next_code command - if the user does not tell you to use it, do not use it
- This tool retrieves full function bodies, complete class definitions, and entire file contents
- Function and class names must match exactly (case-sensitive)
- Line numbers are 1-indexed
- Use this tool when you need to see the complete implementation, not just metadata
- Folders are not considered nodes, only files, methods, functions, and classes are considered nodes
- IMPORTANT: When using database semantic search, always store relevant results in sutra memory if you are not making changes in current iteration or want this code for later use, as search results will not persist to next iteration

Usage:
<database>
<query_name>query_type</query_name>
<name>identifier_name</name>
<file_path>path/to/file</file_path>
<function_name>function_name</function_name>
<start_line>number</start_line>
<end_line>number</end_line>
<code_content>true|false</code_content>
<fetch_next_code>true|false</fetch_next_code>
</database>

Examples:

1. Get complete function implementation by name:
<database>
<query_name>GET_NODES_BY_EXACT_NAME</query_name>
<name>authenticateUser</name>
<code_content>true</code_content>
</database>

2. Get complete file content with all functions and classes:
<database>
<query_name>GET_CODE_FROM_FILE</query_name>
<file_path>src/utils/helpers.py</file_path>
<code_content>true</code_content>
</database>

3. Get specific lines of code from a file:
<database>
<query_name>GET_CODE_FROM_FILE_LINES</query_name>
<file_path>src/models/user.py</file_path>
<start_line>10</start_line>
<end_line>20</end_line>
</database>

4. Find all functions that call a specific function with their complete code:
<database>
<query_name>GET_FUNCTION_CALLERS</query_name>
<function_name>validateInput</function_name>
<code_content>true</code_content>
</database>

5. Get all function/class names from a file with their complete implementations:
<database>
<query_name>GET_ALL_NODE_NAMES_FROM_FILE</query_name>
<file_path>src/services/auth.py</file_path>
<code_content>true</code_content>
</database>

6. Fetch next chunk of results (only when user explicitly tells you to use fetch_next_code):
<database>
<query_name>GET_ALL_NODE_NAMES_FROM_FILE</query_name>
<file_path>src/services/auth.py</file_path>
<code_content>true</code_content>
<fetch_next_code>true</fetch_next_code>
</database>
"""
