// Search Keyword Tool Prompts

template_string SearchKeywordToolTemplate() #"
====

## search_keyword

Description: Search for keywords or patterns in the codebase using ripgrep. Supports single keywords, multiple patterns (using OR), and regex patterns. Faster than terminal commands and provides line numbers for precise location tracking.

CRITICAL: Use SPECIFIC, TARGETED keywords. Avoid broad "kitchen sink" searches that return massive results and cause token limit issues.

Required Parameters:
  - keyword: The search pattern. Can be:
    Single keyword: "functionName"
    Multiple patterns: "pattern1|pattern2|pattern3" (use with regex=true)
    Regex pattern: "\\.(get|post|put)\\s*\\(" (use with regex=true)

Other Parameters:
  - before_lines: Lines before match (default: 0)
  - after_lines: Lines after match (default: 5)
  - case_sensitive: Case-sensitive search (default: false)
  - regex: Treat keyword as regex pattern (default: false)
  - fetch_next_chunk: Set to true to fetch next chunks of results when more are available (default: false)
  - file_paths: Comma-separated `absolute` file or directory paths to search. Use this when you know specific paths to search.
  - project_name: The name of the project to search within. Use this to search the entire project automatically.

IMPORTANT:
  - DO NOT use both file_paths and project_name together - choose one approach:
    - Use file_paths when you know specific files/directories to search
    - Use project_name when you want to search the entire project
  - If using file_paths, ensure they are absolute paths.

Notes:
  - use `"fetch_next_chunk": true` only when user explicitly tells you there are more results available - do not use preemptively
  - For multiple patterns, use "pattern1|pattern2" with regex=true
  - Use \\b for word boundaries in regex patterns
  - IMPORTANT: Use EITHER file_paths OR project_name, never both together
    - Use file_paths when you know specific files/directories to search
    - Use project_name when you want to search the entire project
  - Either file_paths or project_name must be provided
  - search_keyword is only for searching codebase - do not use for searching file names or directories - use list_files tool for that

Usage:

"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "your_search_pattern",
    "project_name": "your-project-name",
    "file_paths": "/abs/path/to/file1, /abs/path/to/dir2",
    "before_lines": 0,
    "after_lines": 5,
    "case_sensitive": true|false,
    "regex": true|false,
    "fetch_next_chunk": true|false
  }
}

Parameters Examples:

GOOD EXAMPLES:
1. Search specific function in known files/directories (use file_paths):
{
    "keyword": "getUserById",
    "file_paths": "/abs/path/src/services/user-service.ts, /abs/path/src/controllers/user-controller.ts",
    "before_lines": 5,
    "after_lines": 5
  }
}

2. Targeted regex in a specific file (use file_paths):
{
    "keyword": "function\\s+getUserById\\s*\\(",
    "regex": true,
    "file_paths": "/abs/path/src/utils/helpers.ts",
    "before_lines": 0,
    "after_lines": 5
  }
}

3. Specific term across the entire project (use project_name):
{
    "keyword": "FirebaseRealtimeDB",
    "project_name": "my-awesome-project",
    "case_sensitive": true,
    "after_lines": 10
  }
}

4. Targeted import across known files (use file_paths):
{
    "keyword": "import.*redis",
    "regex": true,
    "file_paths": "/abs/path/src/services/cache-service.ts, /abs/path/src/config/database.ts",
    "before_lines": 0,
    "after_lines": 5
  }
}

5. Multiple related functions across the project (use project_name):
{
    "keyword": "getUserData|setUserData|deleteUserData",
    "regex": true,
    "project_name": "user-management-service",
    "before_lines": 0,
    "after_lines": 5
  }
}

BAD EXAMPLES (AVOID THESE):
1. Too broad:
{
    "keyword": "function|class|method|import|export|const|let|var",
    "regex": true,
    "project_name": "any-project"
  }
}

2. Kitchen sink:
{
    "keyword": "user|User|auth|Auth|login|register|session|token|jwt|api",
    "regex": true,
    "project_name": "any-project"
  }
}

"#
