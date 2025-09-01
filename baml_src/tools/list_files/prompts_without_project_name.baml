// List Files Tool Prompts

template_string ListFilesToolWithoutProjectNameTemplate() #"
    ## list_files
    Description: Request to list files and directories within the specified directory. If recursive is true, it will list all files and directories recursively. If recursive is false or not provided, it will only list the top-level contents.

    Parameters:
    - path: The path of the directory to list contents for (relative to the current workspace directory).
    - recursive: (optional) Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.

    Parameter Examples:
    - List files in directory: path: "/home/user/project", recursive: true
    - List files in subdirectory: path: "src/components", recursive: false
"#
