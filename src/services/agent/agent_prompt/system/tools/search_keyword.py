SEARCH_KEYWORD_TOOL = """## search_keyword
Description: Search for specific keywords or phrases in the codebase. Use this tool when you need to find occurrences of a term across files, such as function names, variable names, or specific code patterns. This tool is faster than terminal commands like grep and provides flexible search capabilities. The tool returns results with line numbers for precise location tracking.

Required Parameters:
- keyword: The keyword or phrase to search for in the codebase.

Optional Parameters:
- before_lines: Number of lines to include before the matched line (default: 0).
- after_lines: Number of lines to include after the matched line (default: 2).
- case_sensitive: Whether the search should be case-sensitive (default: false).
- regex: Whether the keyword is a regular expression (default: false).
- file_path: The specific file path to search within (relative to the current workspace directory {current_dir}). If not provided, the search will be performed across all files in the workspace.

Notes:
- When use_regex is true, the search parameter is treated as a regular expression pattern
- When ignore_case is true, the search is case-insensitive regardless of regex mode

Usage:
<search_keyword>
<keyword>specific keyword</keyword>
<before_lines>number</before_lines>
<after_lines>number</after_lines>
<case_sensitive>boolean</case_sensitive>
<regex>boolean</regex>
<file_path>path/to/file</file_path>
</search_keyword>

Examples:

1. Searching for a variable name in a all file:
<search_keyword>
<keyword>myVariable</keyword>
<before_lines>1</before_lines>  
<after_lines>2</after_lines>
<case_sensitive>true</case_sensitive>
<regex>false</regex>
</search_keyword>

2. Searching for a keyword with regex in specific file:
<search_keyword>
<keyword>function\\s+\\w+\\s*\\(.*\\)</keyword>
<case_sensitive>false</case_sensitive>
<regex>true</regex>
<file_path>src/utils.py</file_path>
</search_keyword>
"""
