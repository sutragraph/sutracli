SEARCH_KEYWORD_TOOL = """## search_keyword
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
<search_keyword>
<keyword>search term</keyword>
<before_lines>number</before_lines>
<after_lines>number</after_lines>
<case_sensitive>boolean</case_sensitive>
<regex>boolean</regex>
<file_paths>path/to/file1.js, path/to/file2.ts</file_paths>
</search_keyword>

Usage with project name (auto-resolves to project base path):
<search_keyword>
<keyword>search term</keyword>
<project_name>Project name here</project_name>
<before_lines>number</before_lines>
<after_lines>number</after_lines>
<case_sensitive>boolean</case_sensitive>
<regex>boolean</regex>
</search_keyword>

**DO NOT use both file_paths and project_name together - choose one approach:**

Examples:

1. Searching for a function across multiple specific files:
<search_keyword>
<keyword>getUserById</keyword>
<before_lines>5</before_lines>
<after_lines>5</after_lines>
<case_sensitive>false</case_sensitive>
<regex>false</regex>
<file_paths>/home/user/project/src/services/user-service.ts, /home/user/project/src/controllers/user-controller.ts</file_paths>
</search_keyword>

2. Searching for a pattern with regex in single file:
<search_keyword>
<keyword>function\\s+\\w+\\s*\\(.*\\)</keyword>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<file_paths>/home/user/project/src/utils/helpers.ts</file_paths>
</search_keyword>

3. Searching across entire project using project name:
<search_keyword>
<keyword>FirebaseRealtimeDB</keyword>
<project_name>my-awesome-project</project_name>
<before_lines>0</before_lines>
<after_lines>10</after_lines>
<case_sensitive>true</case_sensitive>
<regex>false</regex>
</search_keyword>

4. Searching for import statements in multiple files:
<search_keyword>
<keyword>import.*redis</keyword>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<file_paths>/home/user/project/src/services/cache-service.ts, /home/user/project/src/config/database.ts, /home/user/project/src/utils/redis-cache.ts</file_paths>
</search_keyword>

5. Searching for multiple patterns (API endpoints) using project name:
<search_keyword>
<keyword>\\b(app|router)\\.(put|PUT)\\s*\\([^)]*apiFunction\\b|\\bapiFunction\\b.*\\b(put|PUT)\\b</keyword>
<project_name>api-server</project_name>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<after_lines>3</after_lines>
<before_lines>1</before_lines>
</search_keyword>

6. Searching for multiple function names using project name:
<search_keyword>
<keyword>getUserData|setUserData|deleteUserData</keyword>
<project_name>user-management-service</project_name>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
</search_keyword>

7. Searching within specific directories using file paths:
<search_keyword>
<keyword>config|Config</keyword>
<file_paths>src/config, src/utils</file_paths>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
</search_keyword>

8. Searching within a project using project name (auto-resolves base path):
<search_keyword>
<keyword>getUserById</keyword>
<project_name>my-awesome-project</project_name>
<before_lines>2</before_lines>
<after_lines>5</after_lines>
<case_sensitive>false</case_sensitive>
<regex>false</regex>
</search_keyword>


"""
