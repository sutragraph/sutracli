LIST_FILES_TOOL = """## list_files
Description: Request to list files and directories within the specified directory. If recursive is true, it will list all files and directories recursively. If recursive is false or not provided, it will only list the top-level contents.

Special behavior: If no path is provided but project_name is specified, the tool will automatically use the project's base path from the database.

Parameters:
- path: (optional) The path of the directory to list contents for (relative to the current workspace directory {current_dir}). If not provided, project_name must be specified.
- project_name: (optional) The name of the project to list files for. When provided without a path, uses the project's base directory from the database.
- recursive: (optional) Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.

Note: Either path or project_name must be provided.



Usage with explicit path:
<list_files>
<path>Directory path here</path>
<recursive>true or false (optional)</recursive>
</list_files>

Usage with project name (auto-resolves to project base path):
<list_files>
<project_name>Project name here</project_name>
<recursive>true or false (optional)</recursive>
</list_files>

Usage with both (path takes precedence, project_name included in response):
<list_files>
<path>Directory path here</path>
<project_name>Project name here</project_name>
<recursive>true or false (optional)</recursive>
</list_files>

Examples:

Example 1: List files in a specific directory
<list_files>
<path>/home/user/project</path>
<recursive>false</recursive>
</list_files>

Example 2: List files in a project using project name (auto-resolves base path)
<list_files>
<project_name>my-awesome-project</project_name>
<recursive>true</recursive>
</list_files>

Example 3: List files with both path and project name
<list_files>
<path>src/components</path>
<project_name>my-awesome-project</project_name>
<recursive>false</recursive>
</list_files>
"""
