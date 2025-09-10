// List Files Tool Prompts

template_string ListFilesToolWithoutProjectNameTemplate() #"
====

## list_files

Description: Request to list files and directories within the specified directory. If recursive is true, it will list all files and directories recursively. If recursive is false or not provided, it will only list the top-level contents.

Parameters:
  - path: The path of the directory to list contents for (relative to the current workspace directory).
  - recursive: (optional) Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.
  - fetch_next_chunk: Set to true to fetch next chunks of results when more are available (default: false)

Note:
  - use `"fetch_next_chunk": true` only when user explicitly tells you there are more results available - do not use preemptively


Usage:
{
  tool_name: "database",
    parameters: {
    "path": "Directory path here",
    "recursive": "true|false"
  }
}

Parameters Examples:

Example 1: List files in a specific directory
{
  "path": "/home/user/project",
  "recursive": true
}

Example 2: List files with both path and project name
{
  "path": "src/components",
  "recursive": false
}
"#
