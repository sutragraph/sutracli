// Search Keyword Tool Prompts

template_string SearchKeywordToolTemplate() #"
    ## search_keyword
    Description: Search for keywords or patterns in the codebase using ripgrep. Supports single keywords, multiple patterns (using OR), and regex patterns. Faster than terminal commands and provides line numbers for precise location tracking.

    Special behavior: If no file_paths provided but project_name is specified, the tool will automatically search within the project's base path.

    Required Parameters:
    - keyword: The search pattern. Can be:
      * Single keyword: "functionName"
      * Multiple patterns: "pattern1|pattern2|pattern3" (use with regex=true)
      * Regex pattern: "\\.(get|post|put)\\s*\\(" (use with regex=true)

    Optional Parameters:
    - before_lines: Lines before match (default: 0)
    - after_lines: Lines after match (default: 10)
    - case_sensitive: Case-sensitive search (default: false)
    - regex: Treat keyword as regex pattern (default: false)
    - file_paths: (optional) Comma-separated file or directory paths to search. Use this when you know specific paths to search.
    - project_name: (optional) The name of the project to search within. Use this to search the entire project automatically.

    Notes:
    - For multiple patterns, use "pattern1|pattern2" with regex=true
    - Use \\b for word boundaries in regex patterns
    - **IMPORTANT: Use EITHER file_paths OR project_name, never both together**
      - Use file_paths when you know specific files/directories to search
      - Use project_name when you want to search the entire project
    - Either file_paths or project_name must be provided

    Usage with explicit file paths:
    {
      "keyword": "search term",
      "before_lines": "number",
      "after_lines": "number",
      "case_sensitive": "boolean",
      "regex": "boolean",
      "file_paths": "path/to/file1.js, path/to/file2.ts"
    }

    Usage with project name (auto-resolves to project base path):
    {
      "keyword": "search term",
      "project_name": "Project name here",
      "before_lines": "number",
      "after_lines": "number",
      "case_sensitive": "boolean",
      "regex": "boolean"
    }

    **DO NOT use both file_paths and project_name together - choose one approach:**

    Examples:

    1. Searching for a function across multiple specific files:
    {
      "keyword": "getUserById",
      "before_lines": 5,
      "after_lines": 5,
      "case_sensitive": false,
      "regex": false,
      "file_paths": "/home/user/project/src/services/user-service.ts, /home/user/project/src/controllers/user-controller.ts"
    }

    2. Searching for a pattern with regex in single file:
    {
      "keyword": "function\\s+\\w+\\s*\\(.*\\)",
      "case_sensitive": false,
      "regex": true,
      "file_paths": "/home/user/project/src/utils/helpers.ts"
    }

    3. Searching across entire project using project name:
    {
      "keyword": "FirebaseRealtimeDB",
      "project_name": "my-awesome-project",
      "before_lines": 0,
      "after_lines": 10,
      "case_sensitive": true,
      "regex": false
    }

    4. Searching for import statements in multiple files:
    {
      "keyword": "import.*redis",
      "case_sensitive": false,
      "regex": true,
      "file_paths": "/home/user/project/src/services/cache-service.ts, /home/user/project/src/config/database.ts, /home/user/project/src/utils/redis-cache.ts"
    }

    5. Searching for multiple patterns (API endpoints) using project name:
    {
      "keyword": "\\b(app|router)\\.(put|PUT)\\s*\\([^)]*apiFunction\\b|\\bapiFunction\\b.*\\b(put|PUT)\\b",
      "project_name": "api-server",
      "case_sensitive": false,
      "regex": true,
      "after_lines": 3,
      "before_lines": 1
    }

    6. Searching for multiple function names using project name:
    {
      "keyword": "getUserData|setUserData|deleteUserData",
      "project_name": "user-management-service",
      "case_sensitive": false,
      "regex": true
    }

    7. Searching within specific directories using file paths:
    {
      "keyword": "config|Config",
      "file_paths": "src/config, src/utils",
      "case_sensitive": false,
      "regex": true
    }

    8. Searching within a project using project name (auto-resolves base path):
    {
      "keyword": "getUserById",
      "project_name": "my-awesome-project",
      "before_lines": 2,
      "after_lines": 5,
      "case_sensitive": false,
      "regex": false
    }
"#

