template_string SearchKeywordToolWithoutProjectNameTemplate() #"
    ## search_keyword
    Description: Search for keywords or patterns in the codebase using ripgrep. Supports single keywords, multiple patterns (using OR), and regex patterns. Faster than terminal commands and provides line numbers for precise location tracking.

    Required Parameters:
    - keyword: The search pattern. Can be:
      * Single keyword: "functionName"
      * Multiple patterns: "pattern1|pattern2|pattern3" (use with regex=true)
      * Regex pattern: "\\.(get|post|put)\\s*\\(" (use with regex=true)
    - file_paths: Comma-separated file or directory paths to search. Use this when you know specific paths to search.

    Optional Parameters:
    - before_lines: Lines before match (default: 0)
    - after_lines: Lines after match (default: 10)
    - case_sensitive: Case-sensitive search (default: false)
    - regex: Treat keyword as regex pattern (default: false)

    Notes:
    - For multiple patterns, use "pattern1|pattern2" with regex=true
    - Use \\b for word boundaries in regex patterns

    Usage:
    "tool_call": {
      "tool_name": "search_keyword",
      "parameters": {
        "keyword": "your_search_pattern",
        "file_paths": "path/to/file1,path/to/dir2",
        "before_lines": 1,
        "after_lines": 3,
        "case_sensitive": true|false,
        "regex": true|false
      }
    }

    Examples:
    1. Search function in specific files:
    "tool_call": {
      "tool_name": "search_keyword",
      "parameters": {
        "keyword": "getUserById",
        "file_paths": "src/services/user-service.ts, src/controllers/user-controller.ts",
        "before_lines": 1,
        "after_lines": 3
      }
    }

    2. Search with regex:
    "tool_call": {
      "tool_name": "search_keyword",
      "parameters": {
        "keyword": "function\\s+\\w+\\s*\\(.*\\)",
        "regex": true,
        "file_paths": "src/utils/helpers.ts"
        "before_lines": 1
        "after_lines": 3
      }
    }

    3. Search imports:
    "tool_call": {
      "tool_name": "search_keyword",
      "parameters": {
        "keyword": "import.*redis",
        "regex": true,
        "file_paths": "src/services/cache-service.ts, src/config/database.ts"
        "before_lines": 1
        "after_lines": 3
      }
    }
    
    4. Multiple patterns:
    "tool_call": {
      "tool_name": "search_keyword",
      "parameters": {
        "keyword": "\\b(app|router)\\.(put|PUT)\\s*\\([^)]*apiFunction\\b",
        "regex": true,
        "file_paths": "src/api",
        "before_lines": 1
        "after_lines": 3
      }
    }
    
    5. Multiple functions:
    "tool_call": {
      "tool_name": "search_keyword",
      "parameters": {
        "keyword": "getUserData|setUserData|deleteUserData",
        "regex": true,
        "file_paths": "src/config",
        "before_lines": 1
        "after_lines": 3
      }
    }
    
    6. Search directories:
    "tool_call": {
      "tool_name": "search_keyword",
      "parameters": {
        "keyword": "config|Config",
        "file_paths": "src/config, src/utils",
        "regex": true,
        "before_lines": 1
        "after_lines": 3
      }
    }
"#
