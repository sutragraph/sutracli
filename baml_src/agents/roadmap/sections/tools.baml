// Tools Section for Roadmap Agent

template_string RoadmapTools() #"
## AVAILABLE TOOLS

### search_keyword
Description: Search for keywords or patterns in the codebase using ripgrep. Supports single keywords, multiple patterns (using OR), and regex patterns. Faster than terminal commands and provides line numbers for precise location tracking.

Special behavior: If no file_paths provided but project_name is specified, the tool will automatically search within the project's base path.

Parameters:
- keyword (required): The search pattern. Can be:
    * Single keyword: "functionName"
    * Multiple patterns: "pattern1|pattern2|pattern3" (use with regex=true)
    * Regex pattern: "\\.(get|post|put)\\s*\\(" (use with regex=true)
- before_lines (optional): Lines before match (default: 0)
- after_lines (optional): Lines after match (default: 10)
- case_sensitive (optional): Case-sensitive search (default: false)
- regex (optional): Treat keyword as regex pattern (default: false)
- file_paths (optional): Comma-separated file or directory paths to search
- project_name (optional): The name of the project to search within

Notes:
- For multiple patterns, use "pattern1|pattern2" with regex=true
- Use \\b for word boundaries in regex patterns
- Use EITHER file_paths OR project_name, never both together
- Either file_paths or project_name must be provided

### semantic_search
Description: Find similar implementations and patterns in codebase using semantic similarity. Use when you DON'T have specific function/class/file/method names (use database for specific names). Use for discovering existing patterns before creating new code.

Parameters:
- query (required): The search terms to find similar implementations - describe what you're looking for in natural language
- project_name (optional): Name of the project to search within. If not provided, searches across all projects
- fetch_next_code (optional): Set to true to fetch next chunks of results when more are available

Notes:
- Results are delivered in batches for performance
- IMPORTANT: When using semantic search, always store relevant results in sutra memory if you are not making changes in current iteration
- Use descriptive terms that capture the concept you're looking for

### database
Description: Query the project database for files, functions, classes, and metadata. Use for structured queries when you know specific names or want to get hierarchical code structure.

Parameters:
- query_name (required): The type of database query to execute:
    * "GET_FILE_BY_PATH" - Get file content by path
    * "GET_FILE_BLOCK_SUMMARY" - Get summary of code blocks in a file
    * "GET_BLOCK_DETAILS" - Get details of a specific code block
- file_path (optional): Path to the file (required for file-based queries)
- start_line (optional): Start line number for partial file content
- end_line (optional): End line number for partial file content
- block_id (optional): Identifier for specific code block (required for block queries)
- fetch_next_code (optional): Set to true to fetch next chunks when more are available

Notes:
- Prefer GET_FILE_BLOCK_SUMMARY to understand file structure before reading full content
- Use line ranges to get specific sections efficiently
- Store structured results in memory for cross-referencing

### list_files
Description: List files and directories in the project. Use for exploring project structure and finding relevant files.

Parameters:
- path (optional): Directory path to list (if not provided, uses current directory or project base)
- project_name (optional): Project name to list files from (auto-resolves to project base path)
- recursive (optional): Include subdirectories recursively (default: false)
- ignore_patterns (optional): Whether to apply ignore patterns like .gitignore (default: true)

Notes:
- Use project_name to automatically resolve to project's base directory
- Recursive listing provides comprehensive project overview
- Results show directories with trailing "/" for easy identification

### attempt_completion
Description: Complete the current task with a comprehensive roadmap summary. Use when you have gathered sufficient information and can provide complete strategic guidance.

Parameters:
- result (required): Comprehensive task completion summary with strategic roadmap

Notes:
- Only use when you have complete multi-project analysis
- Must include exact file paths, line numbers, and implementation contracts
- Should provide deployment sequence and cross-project coordination requirements
- Result should be independently executable by follow-up agents

## TOOL USAGE STRATEGY

### Recommended Sequence
1. **Start Broad**: Use semantic_search without project_name for ecosystem-wide pattern discovery
2. **Focus Projects**: Use search_keyword or semantic_search WITH project_name for targeted analysis
3. **Get Structure**: Use database GET_FILE_BLOCK_SUMMARY to understand code organization
4. **Drill Down**: Use database GET_FILE_BY_PATH with line ranges for specific implementation details
5. **Cross-Reference**: Use search_keyword across projects to find integration points
6. **Complete**: Use attempt_completion with comprehensive roadmap

### Memory Management
- Store semantic_search results immediately if relevant for future iterations
- Store database query results with project context for cross-referencing
- Track file modifications and project relationships
- Document integration points and API contracts discovered

### Efficiency Guidelines
- Use project_name parameter to limit scope when appropriate
- Prefer block summaries over full file content initially
- Use line ranges to get targeted context efficiently
- Avoid redundant queries for the same information
"#
