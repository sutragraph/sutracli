SEARCH_KEYWORD_TOOL = """## search_keyword
Description: Search for specific keywords or phrases in the codebase. Use this tool when you need to find occurrences of a term across files, such as function names, variable names, or specific code patterns. This tool is faster than terminal commands like grep and provides flexible search capabilities. The tool returns results with line numbers for precise location tracking.

Required Parameters:
- keyword: The keyword or phrase to search for in the codebase.

Optional Parameters:
- before_lines: Number of lines to include before the matched line (default: 5).
- after_lines: Number of lines to include after the matched line (default: 5).
- case_sensitive: Whether the search should be case-sensitive (default: false).
- regex: Whether the keyword is a regular expression (default: false).
- file_paths: Comma-separated list of specific file paths to search within (relative to the current workspace directory {current_dir}). If empty or not provided, the search will be performed across all files in the workspace.

Notes:
- When regex is true, the search parameter is treated as a regular expression pattern
- When case_sensitive is true, the search is case-sensitive regardless of regex mode
- Use file_paths comma-separated string for multiple specific files, or leave empty for whole directory search
- Results include 10 lines of context (5 before + 5 after) by default for better understanding

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
"""
