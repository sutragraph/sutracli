template_string SimpleDatabaseToolTemplate() #"
## database

Query codebase metadata for file info, code blocks, dependencies. Use for structured access to knowledge graph.

Required Parameter:
  - query_name: Defines the type of query to execute.
    Possible values:
      - GET_FILE_BY_PATH — Retrieve full file content.
      - GET_BLOCK_DETAILS — Retrieve block content/connections.

When using GET_FILE_BY_PATH:
  Required:
    - file_path: Full absolute path to the file.
  Optional:
    - start_line: 1-indexed line number to start reading from.
    - end_line: 1-indexed line number to stop reading at.
    - fetch_next_chunk: Boolean flag indicating whether to fetch the next file chunk.

When using GET_BLOCK_DETAILS:
  Required:
    - block_id: Unique identifier for the code block.
"#
