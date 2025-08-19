SEARCH_KEYWORD_TOOL = """## search_keyword
Description: Search for keywords or patterns in the codebase using ripgrep. Supports single keywords, multiple patterns (using OR), and regex patterns. Faster than terminal commands and provides line numbers for precise location tracking.

Required Parameters:
- keyword: The search pattern. Can be:
  * Single keyword: "functionName"
  * Multiple patterns: "pattern1|pattern2|pattern3" (use with regex=true)
  * Regex pattern: "\\.(get|post|put)\\s*\\(" (use with regex=true)

Optional Parameters:
- before_lines: Lines before match (default: 5)
- after_lines: Lines after match (default: 5) 
- case_sensitive: Case-sensitive search (default: false)
- regex: Treat keyword as regex pattern (default: false)
- file_paths: Comma-separated file or directory paths to search, or empty for all files

Notes:
- For multiple patterns, use "pattern1|pattern2" with regex=true
- Leave file_paths empty to search all files when uncertain about locations
- Use \\b for word boundaries in regex patterns

Usage:
<search_keyword>
<keyword>search term</keyword>
<before_lines>number</before_lines>
<after_lines>number</after_lines>
<case_sensitive>boolean</case_sensitive>
<regex>boolean</regex>
<file_paths>path/to/file1.js, path/to/file2.ts</file_paths>
</search_keyword>

Examples:

1. Searching for a function across multiple specific files:
<search_keyword>
<keyword>getUserById</keyword>
<before_lines>5</before_lines>
<after_lines>5</after_lines>
<case_sensitive>false</case_sensitive>
<regex>false</regex>
<file_paths>src/services/user-service.ts, src/controllers/user-controller.ts</file_paths>
</search_keyword>

2. Searching for a pattern with regex in single file:
<search_keyword>
<keyword>function\\s+\\w+\\s*\\(.*\\)</keyword>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<file_paths>src/utils/helpers.ts</file_paths>
</search_keyword>

3. Searching across entire codebase (no file restrictions):
<search_keyword>
<keyword>FirebaseRealtimeDB</keyword>
<before_lines>0</before_lines>
<after_lines>10</after_lines>
<case_sensitive>true</case_sensitive>
<regex>false</regex>
<file_paths></file_paths>
</search_keyword>

4. Searching for import statements in multiple files:
<search_keyword>
<keyword>import.*redis</keyword>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<file_paths>src/services/cache-service.ts, src/config/database.ts, src/utils/redis-cache.ts</file_paths>
</search_keyword>

5. Searching for multiple patterns (API endpoints):
<search_keyword>
<keyword>\\b(app|router)\\.(put|PUT)\\s*\\([^)]*apiFunction\\b|\\bapiFunction\\b.*\\b(put|PUT)\\b</keyword>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<after_lines>3</after_lines>
<before_lines>1</before_lines>
<file_paths></file_paths>
</search_keyword>

6. Searching for multiple function names:
<search_keyword>
<keyword>getUserData|setUserData|deleteUserData</keyword>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<file_paths></file_paths>
</search_keyword>

7. Searching within specific directories:
<search_keyword>
<keyword>config|Config</keyword>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<file_paths>src/config, src/utils</file_paths>
</search_keyword>
"""
