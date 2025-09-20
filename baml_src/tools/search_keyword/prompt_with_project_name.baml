// Search Keyword Tool Prompts

template_string SearchKeywordToolTemplate() #"
## search_keyword

### Description
Search for keywords or patterns in the codebase using ripgrep. Supports single/multiple patterns (via OR) and regex. Use for targeted searches with known terms; prefer over semantic_search for specifics.

### Parameters
- keyword: REQUIRED - Pattern (e.g., "functionName" or "pattern1|pattern2" with regex=true) (type: string).
- before_lines: OPTIONAL - Lines before match (default: 0) (type: int?).
- after_lines: OPTIONAL - Lines after match (default: 5) (type: int?).
- case_sensitive: OPTIONAL - Enable sensitivity (default: false) (type: bool?).
- regex: OPTIONAL - Treat as regex (default: false) (type: bool?).
- fetch_next_chunk: OPTIONAL - For more results (default: false) (type: bool?).
- file_paths: OPTIONAL - Comma-separated absolute paths for targeted search (type: string?).
- project_name: OPTIONAL - For full-project search (type: string?).

### Usage
{
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "pattern",
    "project_name": "project",
    "file_paths": "/path1,/path2",
    "before_lines": 0,
    "after_lines": 5,
    "case_sensitive": false,
    "regex": false,
    "fetch_next_chunk": false
  }
}

### Guidelines
Think step-by-step: 'Goal: Find exact terms? Tool: search_keyword. Why: Precise locations.'
Select one scope: Use file_paths for specific files/dirs or project_name for entire project.
Prioritize 3-5 targeted patterns to focus results; use \b for boundaries in regex.
Fetch next chunk only when indicated.
Use for codebase only; for files/dirs, prefer list_files.
When using `regex: false`, never use pipe `|` or special regex characters in the keyword. Setting regex to false means fixed string matching - it will search for the exact string you provide.

### Examples
1. Function in files:
{
  "keyword": "getUserById",
  "file_paths": "/abs/path/src/services/user-service.ts,/abs/path/src/controllers/user-controller.ts",
  "before_lines": 5,
  "after_lines": 5
}

2. Regex in file:
{
  "keyword": "function\s+getUserById\s*\(",
  "regex": true,
  "file_paths": "/abs/path/src/utils/helpers.ts",
  "before_lines": 0,
  "after_lines": 5
}

3. Term in project:
{
  "keyword": "FirebaseRealtimeDB",
  "project_name": "my-awesome-project",
  "case_sensitive": true,
  "after_lines": 10
}

4. Import in files:
{
  "keyword": "import.*redis",
  "regex": true,
  "file_paths": "/abs/path/src/services/cache-service.ts,/abs/path/src/config/database.ts",
  "before_lines": 0,
  "after_lines": 5
}

5. Multiple functions in project:
{
  "keyword": "getUserData|setUserData|deleteUserData",
  "regex": true,
  "project_name": "user-management-service",
  "before_lines": 0,
  "after_lines": 5
}
"#
