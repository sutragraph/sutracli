// Search Keyword Tool Prompts

template_string SearchKeywordToolTemplate() #"
  ====
    ## search_keyword
    Description: Search for keywords or patterns in the codebase using ripgrep. Supports single keywords, multiple patterns (using OR), and regex patterns. Faster than terminal commands and provides line numbers for precise location tracking.

    **CRITICAL**: Use SPECIFIC, TARGETED keywords. Avoid broad "kitchen sink" searches that return massive results and cause token limit issues.

    Required Parameters:
    - keyword: The search pattern. Can be:
      * Single keyword: "functionName"
      * Multiple patterns: "pattern1|pattern2|pattern3" (use with regex=true)
      * Regex pattern: "\\.(get|post|put)\\s*\\(" (use with regex=true)

    Other Parameters:
    - before_lines: Lines before match (default: 0)
    - after_lines: Lines after match (default: 5)
    - case_sensitive: Case-sensitive search (default: false)
    - regex: Treat keyword as regex pattern (default: false)
    - fetch_next_chunk: Set to true to fetch next chunks of results when more are available (default: false)
    - file_paths: Comma-separated file or directory paths to search. Use this when you know specific paths to search.
    - project_name: The name of the project to search within. Use this to search the entire project automatically.
    
    IMPORTANT: **DO NOT use both file_paths and project_name together - choose one approach:**
      - Use file_paths when you know specific files/directories to search
      - Use project_name when you want to search the entire project

    Notes:
    - use `"fetch_next_chunk": true` only when user explicitly tells you there are more results available - do not use preemptively
    - For multiple patterns, use "pattern1|pattern2" with regex=true
    - Use \\b for word boundaries in regex patterns
    - **IMPORTANT: Use EITHER file_paths OR project_name, never both together**
      - Use file_paths when you know specific files/directories to search
      - Use project_name when you want to search the entire project
    - Either file_paths or project_name must be provided

    Parameter Examples:
    - ✅ GOOD - Specific function: keyword: "getUserById", file_paths: "src/services/user-service.ts, src/controllers/user-controller.ts", before_lines: 5, after_lines: 5
    - ✅ GOOD - Targeted regex: keyword: "function\\s+getUserById\\s*\\(", regex: true, file_paths: "src/utils/helpers.ts"
    - ✅ GOOD - Specific term: keyword: "FirebaseRealtimeDB", project_name: "my-awesome-project", case_sensitive: true, after_lines: 10
    - ✅ GOOD - Targeted import: keyword: "import.*redis", regex: true, file_paths: "src/services/cache-service.ts, src/config/database.ts"
    - ✅ GOOD - Related functions (max 3): keyword: "getUserData|setUserData|deleteUserData", project_name: "user-management-service", regex: true
    - ❌ BAD - Too broad: keyword: "function|class|method|import|export|const|let|var", regex: true
    - ❌ BAD - Kitchen sink: keyword: "user|User|auth|Auth|login|register|session|token|jwt|api", regex: true
"#
