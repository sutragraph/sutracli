// List Files Tool Prompts

template_string ListFilesToolTemplate() #"
## list_files

### Description
List files and directories in a specified path or project. Set recursive for full subtree; default to top-level.

### Parameters
- path: OPTIONAL - Directory path (type: string?).
- project_name: OPTIONAL - For auto-base path (type: string?).
- recursive: OPTIONAL - Enable full listing (default: false) (type: bool?).
- fetch_next_chunk: OPTIONAL - For more results (default: false) (type: bool?).

### Usage
{
  "tool_name": "list_files",
  "parameters": {
    "path": "dir/path",
    "project_name": "project",
    "recursive": true,
    "fetch_next_chunk": true
  }
}

### Guidelines
Think step-by-step: 'Goal: Explore structure? Tool: list_files. Why: File discovery.'
Provide path or project_name; if both, path takes precedence.
Fetch next chunk only when indicated.

### Examples
1. Specific dir recursive:
{
  "path": "/home/user/project",
  "recursive": true
}

2. Project base:
{
  "project_name": "my-awesome-project",
  "recursive": true
}

3. Both (path first):
{
  "path": "src/components",
  "project_name": "my-awesome-project",
  "recursive": false
}
"#
