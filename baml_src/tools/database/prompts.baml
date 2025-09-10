// Database Tool Prompts

template_string DatabaseToolTemplate() #"
====

## database

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
- use `"fetch_next_chunk": true` only when user explicitly tells you there are more results available - do not use preemptively
- Most queries now use file_path directly - the system handles internal ID conversion automatically
- For block-specific operations, you may need block_id (obtained from GET_FILE_BLOCK_SUMMARY)
- Line numbers are 1-indexed
- Use this tool when you need structured codebase information and relationships
- IMPORTANT: When using database queries, always store relevant results in sutra memory if you are not making changes in current iteration or fetching more chunks or using new query or want this code for later use, as search results will not persist to next iteration

Usage:
{
  tool_name: "database",
  parameters: {
    "query_name": "query_type",
    "file_path": "path/to/file",
    "start_line": "start_line_number",
    "end_line": "end_line_number",
    "block_id": "block_identifier",
    "fetch_next_code": "true|false"
  }
}

Parameters Examples:

1. Get file information by path:
{
  "query_name": "GET_FILE_BY_PATH",
  "file_path": "path/to/your/file.py"
}

2. Get specific section of a file:
{
  "query_name": "GET_FILE_BY_PATH",
  "file_path": "path/to/your/file.py",
  "start_line": 10,
  "end_line": 50
}

3. Get all code blocks in a file:
{
  "query_name": "GET_FILE_BLOCK_SUMMARY",
  "file_path": "path/to/your/file.py"
}

4. Get block details:
{
  "query_name": "GET_BLOCK_DETAILS",
  "block_id": "123"
}

5. Fetch next chunk of results (only when user explicitly tells you to use fetch_next_code):
{
  "query_name": "GET_FILE_BLOCK_SUMMARY",
  "file_path": "path/to/your/file.py",
  "fetch_next_code": true
}
"#
