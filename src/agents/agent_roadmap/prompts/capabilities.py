"""
Available tools and capabilities for the Roadmap Agent
"""

CAPABILITIES = """
## Available Tools

**SEMANTIC_SEARCH**: Discover files containing specific implementations, functions, or patterns. Finds files based on semantic meaning and code functionality.

**SEARCH_KEYWORD**: Find exact symbols, function names, import statements, and method calls using regex patterns. Accepts file_paths list to target specific files or searches entire codebase when list is empty. Returns 10 lines of context with line numbers.

**DATABASE_SEARCH**: Query structured code graph for exact content and dependencies:
- GET_FILE_BY_PATH: Complete file content and structure
- GET_FILE_BLOCK_SUMMARY: Function/class overviews within files
- GET_CHILD_BLOCKS: Method details within classes
- GET_FILE_IMPORTS: Dependency analysis and import statements
- GET_DEPENDENCY_CHAIN: Files affected by component changes

**LIST_FILES**: Verify file locations and directory structure. Understand project organization for file creation or path confirmation.

**ATTEMPT_COMPLETION**: Present final implementation specifications with numbered modification steps."""
