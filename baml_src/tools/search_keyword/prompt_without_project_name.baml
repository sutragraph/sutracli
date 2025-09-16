template_string SearchKeywordToolWithoutProjectNameTemplate() #"
====

## search_keyword

Description: Search for keywords or patterns in the codebase using ripgrep. Supports single keywords, multiple patterns (using OR), and regex patterns. Faster than terminal commands and provides line numbers for precise location tracking.

CRITICAL: Use SPECIFIC, TARGETED keywords. Avoid broad "kitchen sink" searches that return massive results and cause token limit issues.

Required Parameters:
  - keyword: The search pattern. Can be:
    Single keyword: "functionName"
    Multiple patterns: "pattern1|pattern2|pattern3" (use with regex=true)
    Regex pattern: "\.(get|post|put)\s*\(" (use with regex=true)

Optional Parameters:
  - before_lines: Lines before match (default: 0)
  - after_lines: Lines after match (default: 5)
  - case_sensitive: Case-sensitive search (default: false)
  - regex: Treat keyword as regex pattern (default: false)
  - file_paths: Comma-separated file or directory paths to search.
  - fetch_next_chunk: Set to true to fetch next chunks of results when more are available (default: false)

Notes:
  - use `"fetch_next_chunk": true` only when user explicitly tells you there are more results available - do not use preemptively
  - For multiple patterns, use "pattern1|pattern2" with regex=true
  - Use \b for word boundaries in regex patterns
  - When results return `No results found for keyword search.`, check the history section for previous search attempts. If you see 3-4 failed search attempts with different keywords/patterns, then mark the task complete. However, don't give up after just 1 failed attempt - try different variations of keywords, patterns, or search parameters before concluding no results exist.
  - search_keyword is only for searching codebase - do not use for searching file names or directories - use list_files tool for that
  - When using `regex: false`, never use pipe `|` or special regex characters in the keyword. Setting regex to false means fixed string matching - it will search for the exact string you provide.
Usage:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "your_search_pattern",
    "file_paths": "path/to/file1, path/to/dir2",
    "before_lines": 0,
    "after_lines": 5,
    "case_sensitive": true|false,
    "regex": true|false,
    "fetch_next_chunk": true|false
  }
}

Examples:

GOOD EXAMPLES:
1. Search specific function in files:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "getUserById",
    "file_paths": ".",
    "before_lines": 0,
    "after_lines": 5
  }
}

2. Targeted regex search:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "function\s+getUserById\s*\(",
    "regex": true,
    "file_paths": "src/utils/helpers.ts"
    "before_lines": 0
    "after_lines": 5
  }
}

3. Specific import search:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "import.*redis",
    "regex": true,
    "file_paths": "src/services/cache-service.ts, src/config/database.ts"
    "before_lines": 0
    "after_lines": 5
  }
}

4. Multiple patterns:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "\b(app|router)\.(put|PUT)\s*\([^)]*apiFunction\b",
    "regex": true,
    "file_paths": "src/api",
    "before_lines": 0
    "after_lines": 5
  }
}

5. Multiple functions:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "getUserData|setUserData|deleteUserData",
    "regex": true,
    "file_paths": "src/config",
    "before_lines": 0
    "after_lines": 5
  }
}

6. Related terms search:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "config|Config",
    "file_paths": "src/config, src/utils",
    "regex": true,
    "before_lines": 0
    "after_lines": 5
  }
}

BAD EXAMPLES: (AVOID THESE)
1. Too broad/kitchen sink:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "function|class|method|import|export|const|let|var",
    "regex": true,
    "file_paths": "src"
  }
}

2. Massive OR search:
"tool_call": {
  "tool_name": "search_keyword",
  "parameters": {
    "keyword": "user|User|auth|Auth|login|register|session|token|jwt|api|controller|service",
    "regex": true,
    "file_paths": "src"
  }
}
"#
