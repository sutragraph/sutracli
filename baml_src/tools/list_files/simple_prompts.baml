template_string SimpleListFilesToolTemplate() #"
## list_files

Request to list files and directories within the specified directory. If recursive is true, it will list all files and directories recursively. If recursive is false or not provided, it will only list the top-level contents.

Required Parameters:
  - path: The absolute path to the directory whose contents (files and folders) should be listed.

Optional Parameters:
  - recursive: Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.
  - fetch_next_chunk: Set to true to fetch next chunks of results when more are available
"#
