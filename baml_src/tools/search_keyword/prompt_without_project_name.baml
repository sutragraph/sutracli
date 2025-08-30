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
    - **IMPORTANT: Use EITHER file_paths OR project_name, never both together**
      - Use file_paths when you know specific files/directories to search
      - Use project_name when you want to search the entire project
    - Either file_paths or project_name must be provided

    Usage with explicit file paths:
    {
      tool_name: "search_keyword",
      parameters: {
        "keyword": "search term",
        "before_lines": "number",
        "after_lines": "number",
        "case_sensitive": "boolean",
        "regex": "boolean",
        "file_paths": "path/to/file1.js, path/to/file2.ts"
      }
    }

    Examples:

    1. Searching for a function across multiple specific files:
    parameters: {
      "keyword": "getUserById",
      "before_lines": 5,
      "after_lines": 5,
      "case_sensitive": false,
      "regex": false,
      "file_paths": "/home/user/project/src/services/user-service.ts, /home/user/project/src/controllers/user-controller.ts"
    }

    2. Searching for a pattern with regex in single file:
    parameters: {
      "keyword": "function\\s+\\w+\\s*\\(.*\\)",
      "case_sensitive": false,
      "regex": true,
      "file_paths": "/home/user/project/src/utils/helpers.ts"
    }

    3. Searching for import statements in multiple files:
    parameters: {
      "keyword": "import.*redis",
      "case_sensitive": false,
      "regex": true,
      "file_paths": "/home/user/project/src/services/cache-service.ts, /home/user/project/src/config/database.ts, /home/user/project/src/utils/redis-cache.ts"
    }

    4. Searching for multiple patterns (API endpoints):
    parameters: {
      "keyword": "\\b(app|router)\\.(put|PUT)\\s*\\([^)]*apiFunction\\b|\\bapiFunction\\b.*\\b(put|PUT)\\b",
      "case_sensitive": false,
      "file_paths": "src/api",
      "regex": true,
      "after_lines": 3,
      "before_lines": 1
    }

    5. Searching for multiple function names:
    parameters: {
      "keyword": "getUserData|setUserData|deleteUserData",
      "case_sensitive": false,
      "file_paths": "src/config",
      "regex": true
    }

    6. Searching within specific directories using file paths:
    parameters: {
      "keyword": "config|Config",
      "file_paths": "src/config, src/utils",
      "case_sensitive": false,
      "regex": true
    }
"#