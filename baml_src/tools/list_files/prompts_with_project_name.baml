// List Files Tool Prompts

template_string ListFilesToolTemplate() #"
====

## list_files
Description: Request to list files and directories within the specified directory. If recursive is true, it will list all files and directories recursively. If recursive is false or not provided, it will only list the top-level contents.

Special behavior: If no path is provided but project_name is specified, the tool will automatically use the project's base path from the database.

Parameters:
- path: (optional) The path of the directory to list contents for (relative to the current workspace directory). If not provided, project_name must be specified.
- project_name: (optional) The name of the project to list files for. When provided without a path, uses the project's base directory from the database.
- recursive: (optional) Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.
- fetch_next_chunk: Set to true to fetch next chunks of results when more are available (default: false)

Note: 
- Either path or project_name must be provided.
- use `"fetch_next_chunk": true` only when user explicitly tells you there are more results available - do not use preemptively

Usage with explicit path:
{
  tool_name: "database",
    parameters: {
    "path": "Directory path here",
    "recursive": "true|false"
  }
}

Usage with project name (auto-resolves to project base path):
{
  tool_name: "database",
    parameters: {
    "project_name": "Project name here",
    "recursive": "true|false"
  }
}

Usage with both (path takes precedence, project_name included in response):
{
  tool_name: "database",
    parameters: {
    "path": "Directory path here",
    "project_name": "Project name here",
    "recursive": "true|false"
  }
}

Parameters Examples:

Example 1: List files in a specific directory
{
  "path": "/home/user/project",
  "recursive": true
}

Example 2: List files in a project using project name (auto-resolves base path)
{
  "project_name": "my-awesome-project",
  "recursive": true
}

Example 3: List files with both path and project name
{
  "path": "src/components",
  "project_name": "my-awesome-project",
  "recursive": false
}
"#
