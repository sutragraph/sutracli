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

    Parameter Examples:
    - Search function in files: keyword: "getUserById", file_paths: "src/services/user-service.ts, src/controllers/user-controller.ts", before_lines: 5, after_lines: 5
    - Search with regex: keyword: "function\\s+\\w+\\s*\\(.*\\)", regex: true, file_paths: "src/utils/helpers.ts"
    - Search imports: keyword: "import.*redis", regex: true, file_paths: "src/services/cache-service.ts, src/config/database.ts"
    - Multiple patterns: keyword: "\\b(app|router)\\.(put|PUT)\\s*\\([^)]*apiFunction\\b", regex: true, file_paths: "src/api", after_lines: 3, before_lines: 1
    - Multiple functions: keyword: "getUserData|setUserData|deleteUserData", regex: true, file_paths: "src/config"
    - Search directories: keyword: "config|Config", file_paths: "src/config, src/utils", regex: true
"#
