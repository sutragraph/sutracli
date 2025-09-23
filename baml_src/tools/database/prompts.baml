// Database Tool Prompts

template_string DatabaseToolTemplate() #"
## database

### Description
Query codebase metadata for file info, code blocks, dependencies. Use for structured access to knowledge graph.

### Parameters
- query_name: REQUIRED - Type (e.g., GET_FILE_BY_PATH) (type: string).
- file_path: OPTIONAL - For file queries (type: string?).
- start_line: OPTIONAL - 1-indexed start (type: int?).
- end_line: OPTIONAL - 1-indexed end (type: int?).
- block_id: OPTIONAL - For block queries (type: string?).
- fetch_next_chunk: OPTIONAL - For more (type: bool?).

### Usage
{
  "tool_name": "database",
  "parameters": {
    "query_name": "GET_FILE_BY_PATH",
    "file_path": "path/file.py",
    "start_line": 10,
    "end_line": 50,
    "block_id": "123",
    "fetch_next_chunk": true
  }
}

### Guidelines
Think step-by-step: 'Goal: Structured info? Tool: database. Why: Relationships/details.'
Use full paths; store results in sutra_memory for persistence if needed.
Fetch next only when indicated.
Query Types:
1. GET_FILE_BY_PATH: File content/language/project (req: file_path; opt: start/end_line).
2. GET_BLOCK_DETAILS: Block content/connections (req: block_id).

### Examples
1. Full file:
{
  "query_name": "GET_FILE_BY_PATH",
  "file_path": "path/to/your/file.py"
}

2. File section:
{
  "query_name": "GET_FILE_BY_PATH",
  "file_path": "path/to/your/file.py",
  "start_line": 10,
  "end_line": 50
}

3. Block:
{
  "query_name": "GET_BLOCK_DETAILS",
  "block_id": "123"
}
"#
