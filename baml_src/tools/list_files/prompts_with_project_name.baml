// List Files Tool Prompts

template_string ListFilesToolTemplate() #"
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

    Parameter Examples:
    - List files in current directory: path: ".", recursive: true
    - List files in specific directory: path: "/path/to/directory", recursive: false
    - List files by project name: project_name: "my-project", recursive: true
    - List with both: path: "src", project_name: "my-project", recursive: true
"#
